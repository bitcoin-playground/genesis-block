# Genesis-Block
Script Python per creare i parametri necessari per un blocco genesis unico con algoritmo SHA256 e supporto per indirizzi SegWit (bech32).

## Caratteristiche
- Algoritmo: **SHA256** (double SHA-256)
- Supporto per indirizzi **bech32** (P2WPKH, P2WSH), **base58** (P2PKH) e chiavi pubbliche (P2PK)
- Mining multi-thread per ottimizzare la ricerca del nonce
- Compatibile con Bitcoin e fork basati su SHA256

## Creazione dell'ambiente virtuale

### Windows

```bash
python -m venv venv
.\venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## Dipendenze
Installa le dipendenze necessarie:

```bash
pip install -r requirements.txt
```

## Esempi di utilizzo

### Generare un genesis block con indirizzo personalizzato

```bash
python genesis.py -p bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4 -z "Il mio timestamp personalizzato"
```


### Generare un genesis block per regtest

```bash
python genesis.py -z "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks" -t 1296688602 -b 0x207fffff -p bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

### Generare un genesis block con indirizzo testnet

```bash
python genesis.py -z "Il mio timestamp per testnet" -p tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx
```

### Generare con timestamp e valore personalizzati

```bash
python genesis.py -z "Blockchain lanciata il 11/11/2025" -t 1731283200 -v 5000000000 -p bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
```

### Specificare il numero di thread

```bash
python genesis.py -z "Il mio timestamp" -p bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4 -w 16
```

## Opzioni disponibili

```
Utilizzo: python genesis.py [opzioni]

Opzioni:
  -h, --help            Mostra questo messaggio di aiuto ed esce

  -t TIME, --time=TIME
                        Il timestamp Unix quando viene creato il blocco genesis
                        (default: timestamp corrente)

  -z TIMESTAMP, --timestamp=TIMESTAMP
                        Il pszTimestamp che si trova nel coinbase del blocco genesis
                        (default: "The Times 03/Jan/2009 Chancellor on brink of second bailout for banks")

  -n NONCE, --nonce=NONCE
                        Il valore iniziale del nonce che verrà incrementato durante
                        la ricerca dell'hash genesis (default: 0)

  -p ADDRESS, --address=ADDRESS
                        L'indirizzo (bech32, base58) o la chiave pubblica (hex) per l'output script (default: bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4)

  -v VALUE, --value=VALUE
                        Il valore in coin per l'output, valore completo
                        (es: per bitcoin 5000000000 = 50 BTC. Per altre coin:
                        Valore Blocco * 100000000) (default: 5000000000)

  -b BITS, --bits=BITS
                        Il target in rappresentazione compatta, associato a una
                        difficoltà di 1 (default: 0x1d00ffff per mainnet,
                        usa 0x207fffff per regtest)

  -w WORKERS, --workers=WORKERS
                        Numero di worker paralleli (core CPU) da utilizzare
                        (default: numero di core del sistema)
```

## Tipi di indirizzi supportati

Lo script supporta tre formati per specificare il destinatario dei fondi:

### 1. Indirizzi bech32 (SegWit)
- **P2WPKH (Pay-to-Witness-Public-Key-Hash)**: Indirizzi con 20 byte di dati (es: `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`).
- **P2WSH (Pay-to-Witness-Script-Hash)**: Indirizzi con 32 byte di dati (es: `bc1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3qccfmv3`).

### 2. Indirizzi base58 (P2PKH)
- **P2PKH (Pay-to-Public-Key-Hash)**: Indirizzi legacy che iniziano solitamente con `1` (es: `1BoatSLRHtKNngkdXEeobR76b53LETtpyT`).

### 3. Chiave pubblica esadecimale (P2PK)
- **P2PK (Pay-to-Public-Key)**: Una chiave pubblica non compressa (65 byte) o compressa (33 byte) in formato esadecimale.

## Note tecniche

### Formato dell'output script
Lo script genera automaticamente un output script SegWit nel formato:
```
OP_<version> <length> <witness_program>
```

Dove:
- **OP_0** (0x00) per witness version 0 (SegWit v0)
- **length** è la lunghezza del witness program (20 per P2WPKH, 32 per P2WSH)
- **witness_program** è l'hash estratto dall'indirizzo bech32

### Algoritmo di mining
Lo script utilizza il doppio SHA-256 per l'algoritmo Proof-of-Work, identico a Bitcoin:
```
genesis_hash = SHA256(SHA256(block_header))
```

### Performance
- Il mining è parallelizzato automaticamente su tutti i core CPU disponibili
- Ogni worker cerca un nonce diverso per massimizzare l'efficienza
- Viene visualizzato il tasso di hash ogni milione di tentativi

## Risoluzione problemi

### Errore "Invalid address"
Assicurati che l'indirizzo o la chiave pubblica siano nel formato corretto:
- **bech32**: `bc1...` (mainnet) o `tb1...` (testnet).
- **base58**: Indirizzi legacy P2PKH (es: `1...`).
- **Chiave pubblica**: Formato esadecimale non compresso (65 byte) o compresso (33 byte).

### Modulo construct non trovato
Installa la versione corretta:
```bash
pip install -r requirements.txt
```

## Differenze con la versione originale
Questa versione modificata include:
- ✅ Supporto esclusivo per SHA256 (rimossi scrypt, X11, X13, X15)
- ✅ Utilizzo di indirizzi bech32, base58 e chiavi pubbliche raw
- ✅ Parametro `--address` invece di `--pubkey`
- ✅ Validazione automatica degli indirizzi
- ✅ Supporto per P2WPKH, P2WSH, P2PKH e P2PK
- ✅ Codice semplificato e ottimizzato

## Supporto per la conversione della difficoltà

Per facilitare la configurazione del genesis block, è incluso lo script `calc_diff.py`. Questo strumento converte un valore di difficoltà (anche decimale) nel formato `nBits` esadecimale e nel `target hash` corrispondente, necessari per il file `chainparams.cpp` del nodo.

**Come usarlo:**

```bash
python calc_diff.py <valore_difficoltà>
```

**Esempio di output:**

```
difficoltà: 1
nBits: 1d00ffff
target hash: 00000000ffff0000000000000000000000000000000000000000000000000000
```

L'output fornito può essere usato direttamente per impostare i parametri di difficoltà della tua blockchain.

## Licenza

Questo progetto è rilasciato sotto la licenza MIT.
