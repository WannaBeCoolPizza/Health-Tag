#!/usr/bin/env python3
"""
patient_to_rfid.py
Reads patient .txt files, encodes them into compact binary packets,
and sends them to the ESP32 over Serial to write to RFID.
"""

import serial
import struct
import os
import glob
import time
import  sys
import argparse

# ─── Packet Format ────────────────────────────────────────────────────────────
# All data is packed into a tight binary struct to fit RFID memory limits.
#
# Header:       2 bytes  magic (0xA5, 0x5A)
# patientId:    2 bytes  uint16
# dateOfBirth:  4 bytes  uint32  (YYYYMMDD)
# dateOfVisit:  4 bytes  uint32  (YYYYMMDD)
# gender:       1 byte   char
# height:       2 bytes  uint16  (cm * 10, e.g. 165.5 → 1655)
# weight:       2 bytes  uint16  (kg * 10)
# bmi:          2 bytes  uint16  (bmi * 100)
# bloodPressure:2 bytes  uint16  (mmHg * 10)
# severityVisit:1 byte   uint8
# name:        32 bytes  null-padded string
# conditions:  32 bytes  null-padded string
# medications: 32 bytes  null-padded string
# familyHx:    32 bytes  null-padded string
# allergyCount: 1 byte   uint8
# per allergy:
#   name:       16 bytes
#   severity:    1 byte
#   symptomCount:1 byte
#   per symptom: 16 bytes (up to 5)
# checksum:     1 byte   XOR of all preceding bytes
#
# Typical total: ~300–400 bytes — fits on MIFARE Classic 4K or NTAG424

MAGIC = bytes([0xA5, 0x5A])

def pad(s: str, length: int) -> bytes:
    """Encode string to fixed-length null-padded bytes."""
    encoded = s.encode('utf-8')[:length]
    return encoded.ljust(length, b'\x00')

def xor_checksum(data: bytes) -> int:
    result = 0
    for b in data:
        result ^= b
    return result

def parse_patient_file(filepath: str) -> dict:
    """Parse key:value patient text file into a dict."""
    patient = {
        'id': 0, 'name': '', 'dob': 0, 'visit': 0,
        'severity': 0, 'gender': 'U', 'height': 0.0,
        'weight': 0.0, 'bp': 0.0,
        'conditions': '', 'medications': '', 'family': '',
        'allergies': []
    }
    current_allergy = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or ':' not in line:
                continue
            key, _, val = line.partition(':')
            key = key.strip().lower()
            val = val.strip()

            if   key == 'id':          patient['id']         = int(val)
            elif key == 'name':        patient['name']        = val
            elif key == 'dob':         patient['dob']         = int(val)
            elif key == 'visit':       patient['visit']       = int(val)
            elif key == 'severity':    patient['severity']    = int(val)
            elif key == 'gender':      patient['gender']      = val[0].upper()
            elif key == 'height':      patient['height']      = float(val)
            elif key == 'weight':      patient['weight']      = float(val)
            elif key == 'bp':          patient['bp']          = float(val)
            elif key == 'conditions':  patient['conditions']  = val
            elif key == 'medications': patient['medications'] = val
            elif key == 'family':      patient['family']      = val
            elif key == 'allergy':
                name, _, sev = val.partition(',')
                current_allergy = {
                    'name': name.strip(),
                    'severity': int(sev.strip()) if sev.strip() else 0,
                    'symptoms': []
                }
                patient['allergies'].append(current_allergy)
            elif key == 'symptom' and current_allergy:
                current_allergy['symptoms'].append(val)

    return patient

def encode_patient(p: dict) -> bytes:
    """Pack patient dict into binary packet."""
    buf = bytearray()
    buf += MAGIC
    buf += struct.pack('>H', p['id'])
    buf += struct.pack('>I', p['dob'])
    buf += struct.pack('>I', p['visit'])
    buf += p['gender'].encode('ascii')[:1]
    buf += struct.pack('>H', int(p['height'] * 10))
    buf += struct.pack('>H', int(p['weight'] * 10))

    h_m = p['height'] / 100.0
    bmi = (p['weight'] / (h_m * h_m)) if h_m > 0 else 0.0
    buf += struct.pack('>H', int(bmi * 100))

    buf += struct.pack('>H', int(p['bp'] * 10))
    buf += struct.pack('B', p['severity'])
    buf += pad(p['name'],        32)
    buf += pad(p['conditions'],  32)
    buf += pad(p['medications'], 32)
    buf += pad(p['family'],      32)

    allergies = p['allergies'][:5]
    buf += struct.pack('B', len(allergies))
    for a in allergies:
        buf += pad(a['name'], 16)
        buf += struct.pack('B', a['severity'])
        symptoms = a['symptoms'][:5]
        buf += struct.pack('B', len(symptoms))
        for s in symptoms:
            buf += pad(s, 16)
        # pad remaining symptom slots
        for _ in range(5 - len(symptoms)):
            buf += b'\x00' * 16

    # pad remaining allergy slots
    for _ in range(5 - len(allergies)):
        buf += b'\x00' * (16 + 1 + 1 + 5 * 16)

    checksum = xor_checksum(buf)
    buf += struct.pack('B', checksum)
    return bytes(buf)

def send_to_esp32(packet: bytes, port: str, baud: int = 115200):
    """Send encoded packet to ESP32 over serial."""
    print(f"Connecting to {port} @ {baud} baud... - RFID.py:146")
    with serial.Serial(port, baud, timeout=5) as ser:
        time.sleep(2)  # wait for ESP32 reset

        # Framing: LENGTH (4 bytes big-endian) + PACKET
        frame = struct.pack('>I', len(packet)) + packet
        ser.write(frame)
        print(f"Sent {len(frame)} bytes - RFID.py:153")

        # Wait for ESP32 ACK
        deadline = time.time() + 10
        while time.time() < deadline:
            if ser.in_waiting:
                response = ser.readline().decode('utf-8', errors='replace').strip()
                print(f"ESP32: {response} - RFID.py:160")
                if response.startswith("ACK") or response.startswith("ERR"):
                    break

def process_folder(folder: str, port: str, baud: int = 115200):
    """Find all .txt files in folder and write each to RFID."""
    files = sorted(glob.glob(os.path.join(folder, '*.txt')))
    if not files:
        print(f"No .txt files found in {folder} - RFID.py:168")
        return

    for filepath in files:
        print(f"\nProcessing: {os.path.basename(filepath)} - RFID.py:172")
        patient = parse_patient_file(filepath)
        packet  = encode_patient(patient)
        print(f"Patient ID {patient['id']}  {patient['name']} - RFID.py:175")
        print(f"Encoded size: {len(packet)} bytes - RFID.py:176")

        if port:
            print(">>> Place RFID tag on reader, then press Enter... - RFID.py:179")
            input()
            send_to_esp32(packet, port, baud)
        else:
            # Dry-run: just dump hex
            print("Hex preview: - RFID.py:184", packet.hex(' '))

# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder     = sys.argv[1] if len(sys.argv) > 1 else script_dir
    port       = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Converting patient files in: {os.path.abspath(folder)}\n - RFID.py:193")

    files = sorted(glob.glob(os.path.join(folder, '*.txt')))
    if not files:
        print("No .txt files found - RFID.py:197")
        sys.exit(1)

    for filepath in files:
        patient = parse_patient_file(filepath)
        packet  = encode_patient(patient)
        print(f"{os.path.basename(filepath)}  ({len(packet)} bytes) - RFID.py:203")

        if port:
            print(f">>> Place RFID tag on reader then press Enter... - RFID.py:206")
            input()
            send_to_esp32(packet, port)
        else:
            out_path = os.path.splitext(filepath)[0] + '.bin'
            with open(out_path, 'wb') as f:
                f.write(packet)
            print(f"Saved → {os.path.basename(out_path)} - RFID.py:213")

    print("\nDone. - RFID.py:215")