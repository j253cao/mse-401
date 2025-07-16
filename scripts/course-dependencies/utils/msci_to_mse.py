import json
import os

def transform_msci_to_mse(data):
    """
    Transform all keys starting with 'MSCI' to start with 'MSE' instead.
    Preserves the rest of the course code (numbers).
    """
    transformed_data = {}
    for key, value in data.items():
        new_key = key.replace('MSCI', 'MSE') if key.startswith('MSCI') else key
        transformed_data[new_key] = value
    return transformed_data

def main():
    # Get the project root directory (2 levels up from this script)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    # Define input and output file paths
    input_file = os.path.join(project_root, 'data', 'waterloo-open-api-data.json')
    
    # Read the input file
    print("Reading input file...")
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Transform the data
    print("Transforming MSCI to MSE...")
    transformed_data = transform_msci_to_mse(data)
    
    # Write back to the same file
    print("Writing transformed data...")
    with open(input_file, 'w') as f:
        json.dump(transformed_data, f, indent=2)
    
    print("Transformation complete!")

if __name__ == "__main__":
    main() 