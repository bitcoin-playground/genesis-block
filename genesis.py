import hashlib, binascii, struct, array, os, time, sys, optparse
from multiprocessing import Process, Event, Queue

from construct import *


# Bech32 decoding functions
def bech32_polymod(values):
  GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
  chk = 1
  for v in values:
    b = chk >> 25
    chk = (chk & 0x1ffffff) << 5 ^ v
    for i in range(5):
      chk ^= GEN[i] if ((b >> i) & 1) else 0
  return chk


def bech32_hrp_expand(hrp):
  return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def bech32_verify_checksum(hrp, data):
  return bech32_polymod(bech32_hrp_expand(hrp) + data) == 1


def bech32_decode(bech):
  if ((any(ord(x) < 33 or ord(x) > 126 for x in bech)) or
      (bech.lower() != bech and bech.upper() != bech)):
    return (None, None)
  bech = bech.lower()
  pos = bech.rfind('1')
  if pos < 1 or pos + 7 > len(bech) or len(bech) > 90:
    return (None, None)
  if not all(x in 'qpzry9x8gf2tvdw0s3jn54khce6mua7l' for x in bech[pos+1:]):
    return (None, None)
  hrp = bech[:pos]
  data = [('qpzry9x8gf2tvdw0s3jn54khce6mua7l'.index(x)) for x in bech[pos+1:]]
  if not bech32_verify_checksum(hrp, data):
    return (None, None)
  return (hrp, data[:-6])


def convertbits(data, frombits, tobits, pad=True):
  acc = 0
  bits = 0
  ret = []
  maxv = (1 << tobits) - 1
  max_acc = (1 << (frombits + tobits - 1)) - 1
  for value in data:
    if value < 0 or (value >> frombits):
      return None
    acc = ((acc << frombits) | value) & max_acc
    bits += frombits
    while bits >= tobits:
      bits -= tobits
      ret.append((acc >> bits) & maxv)
  if pad:
    if bits:
      ret.append((acc << (tobits - bits)) & maxv)
  elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
    return None
  return ret


def decode_segwit_address(addr):
  hrp, data = bech32_decode(addr)
  if hrp is None:
    return (None, None)
  decoded = convertbits(data[1:], 5, 8, False)
  if decoded is None or len(decoded) < 2 or len(decoded) > 40:
    return (None, None)
  if data[0] > 16:
    return (None, None)
  if data[0] == 0 and len(decoded) != 20 and len(decoded) != 32:
    return (None, None)
  return (data[0], decoded)


def main():
  options = get_args()

  input_script  = create_input_script(options.timestamp)
  output_script = create_output_script(options.address)
  # hash merkle root is the double sha256 hash of the transaction(s) 
  tx = create_transaction(input_script, output_script,options)
  hash_merkle_root = hashlib.sha256(hashlib.sha256(tx).digest()).digest()
  print_block_info(options, hash_merkle_root)

  block_header        = create_block_header(hash_merkle_root, options.time, options.bits, options.nonce)
  if options.workers and options.workers > 1:
    genesis_hash, nonce = generate_hash_parallel(block_header, options.nonce, options.bits, options.workers)
  else:
    genesis_hash, nonce = generate_hash(block_header, options.nonce, options.bits)
  announce_found_genesis(genesis_hash, nonce)


def get_args():
  parser = optparse.OptionParser()
  parser.add_option("-t", "--time", dest="time", default=int(time.time()), 
                   type="int", help="the (unix) time when the genesisblock is created")
  parser.add_option("-z", "--timestamp", dest="timestamp", default="The Times 03/Jan/2009 Chancellor on brink of second bailout for banks",
                   type="string", help="the pszTimestamp found in the coinbase of the genesisblock")
  parser.add_option("-n", "--nonce", dest="nonce", default=0,
                   type="int", help="the first value of the nonce that will be incremented when searching the genesis hash")
  parser.add_option("-p", "--address", dest="address", default="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                   type="string", help="the bech32 address for the output script (e.g., bc1q... for mainnet, tb1q... for testnet)")
  parser.add_option("-v", "--value", dest="value", default=5000000000,
                   type="int", help="the value in coins for the output, full value (exp. in bitcoin 5000000000 - To get other coins value: Block Value * 100000000)")
  parser.add_option("-b", "--bits", dest="bits",
                   type="int", help="the target in compact representation, associated to a difficulty of 1")
  parser.add_option("-w", "--workers", dest="workers",
                   type="int", help="number of parallel workers (CPU cores) to use")

  (options, args) = parser.parse_args()
  if not options.bits:
    options.bits = 0x1d00ffff
  if not options.workers:
    try:
      options.workers = os.cpu_count() or 1
    except Exception:
      options.workers = 1
  return options


def create_input_script(psz_timestamp):
  psz_prefix = ""
  #use OP_PUSHDATA1 if required
  if len(psz_timestamp) > 76: psz_prefix = '4c'

  # length of timestamp as single byte hex
  len_byte_hex = '{:02x}'.format(len(psz_timestamp))
  script_prefix = '04ffff001d0104' + psz_prefix + len_byte_hex
  msg_hex = binascii.hexlify(psz_timestamp.encode('utf-8')).decode('ascii')
  print(script_prefix + msg_hex)
  return binascii.unhexlify(script_prefix + msg_hex)


def create_output_script(address):
  # Decode bech32 address to get witness version and witness program
  witness_version, witness_program = decode_segwit_address(address)

  if witness_version is None:
    sys.exit("Error: Invalid bech32 address")

  # Convert witness program list to bytes
  witness_bytes = bytes(witness_program)

  # Create SegWit output script: OP_<version> <length> <witness_program>
  # OP_0 = 0x00, OP_1 = 0x51, etc.
  if witness_version == 0:
    version_opcode = 0x00
  else:
    version_opcode = 0x50 + witness_version

  script_len = len(witness_bytes)

  # Build the output script
  output_script = bytes([version_opcode, script_len]) + witness_bytes

  return output_script


def create_transaction(input_script, output_script,options):
  output_script_len = len(output_script)
  transaction = Struct("transaction",
    Bytes("version", 4),
    Byte("num_inputs"),
    StaticField("prev_output", 32),
    UBInt32('prev_out_idx'),
    Byte('input_script_len'),
    Bytes('input_script', len(input_script)),
    UBInt32('sequence'),
    Byte('num_outputs'),
    Bytes('out_value', 8),
    Byte('output_script_len'),
    Bytes('output_script',  output_script_len),
    UBInt32('locktime'))

  tx = transaction.parse(b'\x00' * (127 + len(input_script) - 0x43 + output_script_len))
  tx.version           = struct.pack('<I', 1)
  tx.num_inputs        = 1
  tx.prev_output       = struct.pack('<qqqq', 0,0,0,0)
  tx.prev_out_idx      = 0xFFFFFFFF
  tx.input_script_len  = len(input_script)
  tx.input_script      = input_script
  tx.sequence          = 0xFFFFFFFF
  tx.num_outputs       = 1
  tx.out_value         = struct.pack('<q' ,options.value)#0x000005f5e100)#012a05f200) #50 coins
  #tx.out_value         = struct.pack('<q' ,0x000000012a05f200) #50 coins
  tx.output_script_len = output_script_len
  tx.output_script     = output_script
  tx.locktime          = 0
  return transaction.build(tx)


def create_block_header(hash_merkle_root, time, bits, nonce):
  block_header = Struct("block_header",
    Bytes("version",4),
    Bytes("hash_prev_block", 32),
    Bytes("hash_merkle_root", 32),
    Bytes("time", 4),
    Bytes("bits", 4),
    Bytes("nonce", 4))

  genesisblock = block_header.parse(b'\x00' * 80)
  genesisblock.version          = struct.pack('<I', 1)
  genesisblock.hash_prev_block  = struct.pack('<qqqq', 0,0,0,0)
  genesisblock.hash_merkle_root = hash_merkle_root
  genesisblock.time             = struct.pack('<I', time)
  genesisblock.bits             = struct.pack('<I', bits)
  genesisblock.nonce            = struct.pack('<I', nonce)
  return block_header.build(genesisblock)


# https://en.bitcoin.it/wiki/Block_hashing_algorithm
def generate_hash(data_block, start_nonce, bits):
  print('Searching for genesis hash..')
  nonce           = start_nonce
  last_updated    = time.time()
  # https://en.bitcoin.it/wiki/Difficulty
  target = (bits & 0xffffff) * 2**(8*((bits >> 24) - 3))

  while True:
    header_hash  = generate_hashes_from_block(data_block)
    last_updated = calculate_hashrate(nonce, last_updated)
    if is_genesis_hash(header_hash, target):
      return (header_hash, nonce)
    else:
      nonce      = nonce + 1
      data_block = data_block[0:len(data_block) - 4] + struct.pack('<I', nonce)  


def nonce_worker(header_prefix, start_nonce, step, target, result_queue, stop_event):
  nonce = start_nonce
  while not stop_event.is_set():
    data_block  = header_prefix + struct.pack('<I', nonce)
    header_hash = generate_hashes_from_block(data_block)
    if int(binascii.hexlify(header_hash).decode('ascii'), 16) < target:
      result_queue.put((header_hash, nonce))
      stop_event.set()
      break
    nonce += step


def generate_hash_parallel(data_block, start_nonce, bits, workers):
  print('Searching for genesis hash with {} workers..'.format(workers))
  target        = (bits & 0xffffff) * 2**(8*((bits >> 24) - 3))
  header_prefix = data_block[0:len(data_block) - 4]
  stop_event    = Event()
  result_queue  = Queue()
  processes     = []

  for wid in range(workers):
    p = Process(target=nonce_worker, args=(header_prefix, start_nonce + wid, workers, target, result_queue, stop_event))
    p.daemon = True
    p.start()
    processes.append(p)

  # Block until a worker finds the genesis
  result_hash, result_nonce = result_queue.get()
  stop_event.set()

  # Ensure all workers exit cleanly
  for p in processes:
    try:
      p.join(timeout=1)
    except Exception:
      pass

  return result_hash, result_nonce


def generate_hashes_from_block(data_block):
  header_hash = hashlib.sha256(hashlib.sha256(data_block).digest()).digest()[::-1]
  return header_hash


def is_genesis_hash(header_hash, target):
  return int(binascii.hexlify(header_hash).decode('ascii'), 16) < target


def calculate_hashrate(nonce, last_updated):
  if nonce % 1000000 == 999999:
    now             = time.time()
    hashrate        = round(1000000/(now - last_updated))
    generation_time = round(pow(2, 32) / hashrate / 3600, 1)
    sys.stdout.write("\r%s hash/s, estimate: %s h"%(str(hashrate), str(generation_time)))
    sys.stdout.flush()
    return now
  else:
    return last_updated


def print_block_info(options, hash_merkle_root):
  print("algorithm: SHA256")
  print("merkle hash: "  + binascii.hexlify(hash_merkle_root[::-1]).decode('ascii'))
  print("pszTimestamp: " + options.timestamp)
  print("address: "      + options.address)
  print("time: "         + str(options.time))
  print("bits: "         + str(hex(options.bits)))


def announce_found_genesis(genesis_hash, nonce):
  print("genesis hash found!")
  print("nonce: "        + str(nonce))
  print("genesis hash: " + binascii.hexlify(genesis_hash).decode('ascii'))


if __name__ == '__main__':
  main()
