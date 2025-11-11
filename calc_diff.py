#!/usr/bin/env python3
"""
Script per calcolare la difficoltà in formato bits (nBits) e il target hash in formato esadecimale
a partire da un numero di difficoltà (anche minore di 1).
"""

import sys


def difficulty_to_target(difficulty):
    """
    Converte la difficoltà in target hash (256 bit).

    Args:
        difficulty: numero di difficoltà (può essere < 1)

    Returns:
        target hash come intero
    """
    # Target massimo (difficoltà = 1)
    # Questo è il target del blocco genesis di Bitcoin
    max_target = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

    if difficulty <= 0:
        raise ValueError("La difficoltà deve essere maggiore di 0")

    # Calcola il target: target = max_target / difficulty
    target = int(max_target / difficulty)

    return target


def target_to_bits(target):
    """
    Converte un target hash in formato compatto (nBits).

    Il formato nBits è composto da:
    - 1 byte per l'esponente (quanti byte occupa il numero)
    - 3 byte per la mantissa (i 3 byte più significativi)

    Args:
        target: target hash come intero

    Returns:
        nBits in formato compatto (intero)
    """
    # Converte il target in bytes (big-endian)
    target_bytes = target.to_bytes(32, byteorder='big')

    # Trova il primo byte non-zero
    # Questo determina la lunghezza in byte
    start_idx = 0
    while start_idx < len(target_bytes) and target_bytes[start_idx] == 0:
        start_idx += 1

    if start_idx == len(target_bytes):
        return 0

    # L'esponente è il numero di byte dal primo byte non-zero alla fine
    exponent = len(target_bytes) - start_idx

    # Estrai i primi 3 byte come mantissa
    if exponent <= 3:
        mantissa_bytes = target_bytes[start_idx:] + b'\x00' * (3 - exponent)
        exponent = 3
    else:
        mantissa_bytes = target_bytes[start_idx:start_idx+3]

    mantissa = int.from_bytes(mantissa_bytes, byteorder='big')

    # Se il bit più significativo della mantissa è 1 (segno negativo),
    # shifta di un byte e incrementa l'esponente
    if mantissa & 0x800000:
        mantissa >>= 8
        exponent += 1

    # Combina esponente e mantissa: esponente (1 byte) + mantissa (3 byte)
    bits = (exponent << 24) | mantissa

    return bits


def bits_to_target(bits):
    """
    Converte nBits in formato compatto nel target hash.
    (Funzione inversa per verifica)

    Args:
        bits: nBits in formato compatto

    Returns:
        target hash come intero
    """
    exponent = bits >> 24
    mantissa = bits & 0xffffff

    if exponent <= 3:
        target = mantissa >> (8 * (3 - exponent))
    else:
        target = mantissa * (2 ** (8 * (exponent - 3)))

    return target


def format_hex_extended(value, bits=256):
    """
    Formatta un intero come stringa esadecimale di lunghezza fissa.

    Args:
        value: intero da formattare
        bits: numero di bit (default 256)

    Returns:
        stringa esadecimale senza prefisso 0x (formato Bitcoin Core JSON)
    """
    hex_digits = bits // 4
    return format(value, '0%dx' % hex_digits)


def main():
    if len(sys.argv) != 2:
        print("Uso: python calc_diff.py <difficoltà>")
        sys.exit(1)

    try:
        difficulty = float(sys.argv[1])
    except ValueError:
        print("Errore: la difficoltà deve essere un numero valido")
        sys.exit(1)

    if difficulty <= 0:
        print("Errore: la difficoltà deve essere maggiore di 0")
        sys.exit(1)

    target = difficulty_to_target(difficulty)
    bits = target_to_bits(target)

    print(f"difficoltà: {int(difficulty)}")
    print(f"nBits: {format(bits, '08x')}")
    print(f"target hash: {format_hex_extended(target)}")


if __name__ == '__main__':
    main()
