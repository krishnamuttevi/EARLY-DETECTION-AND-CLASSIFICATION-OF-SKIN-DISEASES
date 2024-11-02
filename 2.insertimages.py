import os
import base64
import happybase

# Replace 'localhost' with your HBase server address if it's different
connection = happybase.Connection('localhost', port=9090)

# Define folder names and corresponding table names (dis0 to dis10)
folders_and_tables = {
    "AtopicDermatitis": "dis0",
    "Basal Cell Carcinoma": "dis1",
    "Benign_Keratosis-like_Lesions": "dis2",
    "Eczema": "dis3",
    "Melanocytic_Nevi": "dis4",
    "Melanoma": "dis5",
    "Psoriasis_pictures_Lichen_Planus_and_related_diseases": "dis6",
    "Seborrheic_Keratoses_and_other_Benign_Tumors": "dis7",
    "Tinea_Ringworm_Candidiasis_and_other_Fungal_Infections": "dis8",
    "Warts_Molluscum_and_other_Viral_Infections": "dis9"
}

# Column families
column_families = {
    'image_data': dict()
}

# Define the base directory containing the class folders
base_directory = r"D:\temp\hadtmp"

for folder_name, table_name in folders_and_tables.items():
    # Check if the table already exists, otherwise create it
    if table_name.encode() in connection.tables():
        print(f"Table {table_name} already exists.")
    else:
        # Create the table with column families
        connection.create_table(table_name, column_families)
        print(f"Table {table_name} created successfully with 'image_data' column family.")

    # Define the directory containing the images for the current class
    image_directory = os.path.join(base_directory, folder_name)

    # Access the table
    table = connection.table(table_name)

    # Iterate through the images in the folder
    for image_name in os.listdir(image_directory):
        image_path = os.path.join(image_directory, image_name)
        # Check if it's an image file
        if os.path.isfile(image_path) and image_name.lower().endswith(('png', 'jpg', 'jpeg', 'bmp')):
            # Read the image and encode it in base64
            with open(image_path, 'rb') as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            # Insert the encoded image into HBase
            row_key = image_name.split('.')[0]  # Use the image name (without extension) as the row key
            table.put(row_key, {'image_data:image': encoded_image})
            print(f"Inserted image '{image_name}' into HBase table '{table_name}'.")

# Close the connection
connection.close()