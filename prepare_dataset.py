from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np


def main():
    # Define load and save path
    load_path = Path("/media/nvme1/pbecg-data/fda")
    save_path = Path("/media/nvme1/pbecg-data/dataset")
    # Loop through all the xml files in folder
    for file_path in load_path.rglob("*.xml"):
        # Extract ECG signal
        ecg_data = extract_ecg_data(file_path)
        # Extract annotation
        subject_id, seq_id = save_ecg(save_path, ecg_data)
        print(f"Subject {subject_id} | Sequence {seq_id} Saved.")


def extract_ecg_data(data_path):
    # Extract root of XML file
    tree = ET.parse(data_path)
    root = tree.getroot()
    
    # Define the namespace
    namespaces = {"ns": "urn:hl7-org:v3"}

    # Extract the sequence id and other sequence related metadata
    seq_id = root.find(".//ns:id", namespaces).attrib["root"]
    subject_id = root.find(".//ns:trialSubject/ns:id", namespaces).attrib["extension"]
    acq_time = root.find(".//ns:effectiveTime/ns:low", namespaces).attrib["value"]

    # Initialize a dictionary to hold the ECG data
    ecg_data = {
        "seq_id": seq_id,
        "subject_id": subject_id,
        "acq_time": acq_time,
        "leads": {}
    }

    # Define a mapping for lead names to handle capitalization
    lead_name_mapping = {
        'MDC_ECG_LEAD_AVR': 'MDC_ECG_LEAD_aVR',
        'MDC_ECG_LEAD_AVL': 'MDC_ECG_LEAD_aVL',
        'MDC_ECG_LEAD_AVF': 'MDC_ECG_LEAD_aVF'
    }

    # Extract the ECG signal, unit, and scale
    for component in root.findall(".//ns:sequenceSet/ns:component", namespaces)[1:13]:
        sequence = component.find(".//ns:sequence", namespaces)
        if sequence is not None:
            lead = sequence.find(".//ns:code", namespaces).attrib["code"]
            # Normalize lead name
            lead = lead_name_mapping.get(lead, lead).split("_")[-1]
            scale = float(sequence.find(".//ns:scale", namespaces).attrib["value"])
            unit = sequence.find(".//ns:origin", namespaces).attrib["unit"]
            signal = [int(x) for x in sequence.find(".//ns:digits", namespaces).text.strip().split()]
            ecg_data["leads"][lead] = signal
            ecg_data["scale"] = scale
            ecg_data["unit"] = unit
    
    return ecg_data


def save_ecg(save_path, ecg_data):
    # Directory and file setup
    subject_dir = save_path / ecg_data["subject_id"]
    dat_filename = subject_dir / f"{ecg_data['seq_id']}.dat"
    header_filename = subject_dir / f"{ecg_data['seq_id']}.hea"

    # Create the subject directory if it doesn't exist
    subject_dir.mkdir(parents=True, exist_ok=True)
    
    num_samples = len(next(iter(ecg_data["leads"].values())))
    num_leads = len(ecg_data["leads"])

    # Initialize empty numpy array to store ECG data
    ecg_array = np.zeros((num_samples, num_leads), dtype=np.int16)
    lead_order = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

    # Fill the array with data in the correct lead order
    for i, lead in enumerate(lead_order):
        ecg_array[:, i] = np.array(ecg_data["leads"].get(lead, [0] * num_samples), dtype=np.int16)

    # Write the data to .dat file
    with dat_filename.open("wb") as file:
        ecg_array.tofile(file)
    
    # Create the header file
    with header_filename.open("w") as file:
        # Header line
        file.write(f"{ecg_data['seq_id']} {num_leads} 1000 {num_samples}\n")
        # Write individual lead information
        for lead in lead_order:
            line = f"{ecg_data['seq_id']}.dat 16 {ecg_data['scale']}({0})/{ecg_data['unit']} {lead}\n"
            file.write(line.strip() + "\n")
        # Write acquisition time
        file.write(f"# Acquisition Time: {ecg_data['acq_time']}\n")
    
    return ecg_data["subject_id"], ecg_data["seq_id"]


if __name__ == "__main__":
    main()