"""
Census tract demographic analysis and visualization.

This module provides functionality to:
1. Download census tract data using the pygris package
2. Process PL 94-171 redistricting demographic data files 
3. Create choropleth maps showing dominant racial/ethnic groups by census tract

The main workflow involves:
- Downloading tract geometries for a given state
- Reading and processing demographic data from PL files
- Merging demographic data with tract geometries
- Creating visualizations of racial/ethnic distributions
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pygris import tracts


def get_tracts(state: str) -> gpd.GeoDataFrame:
    """
    Download census tracts for a given state using pygris.
    
    Args:
        state: Two-digit FIPS code for the state (e.g. '48' for Texas)
        
    Returns:
        GeoDataFrame containing census tract geometries and metadata
    """
    print(f"Downloading census tracts for state {state}...")
    tracts_gdf = tracts(state=state, year=2020)
    
    # Ensure GEOID is properly formatted as string
    tracts_gdf['GEOID'] = tracts_gdf['GEOID'].astype(str)
    
    return tracts_gdf


def read_pl_file(file_path: str) -> pd.DataFrame:
    """
    Read PL 94-171 redistricting data file with multiple encoding attempts.
    
    Args:
        file_path: Path to the PL data file
        
    Returns:
        DataFrame containing the PL file data
        
    Raises:
        ValueError: If file cannot be read with any supported encoding
    """
    encodings = ['latin1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            return pd.read_csv(file_path,
                             delimiter='|',
                             dtype=str, 
                             encoding=encoding,
                             low_memory=False)
        except UnicodeDecodeError:
            continue
    
    raise ValueError(f"Could not read file {file_path} with any supported encoding")


def read_pl_data(geo_file_path: str, part1_file_path: str) -> pd.DataFrame:
    """
    Process PL 94-171 redistricting data files to create demographic dataset.
    
    Args:
        geo_file_path: Path to geographic header file
        part1_file_path: Path to Part 1 demographic file
        
    Returns:
        DataFrame containing processed demographic data by tract
    """
    # Read input files
    print("Reading geographic header file...")
    geo_df = read_pl_file(geo_file_path)
    print("Reading Part 1 demographic file...")
    part1_df = read_pl_file(part1_file_path)
    
    print("Processing demographic data...")
    
    # Create demographics DataFrame with population counts
    demographics = pd.DataFrame({
        'total_pop': pd.to_numeric(part1_df.iloc[:, 6], errors='coerce'),
        'white_alone': pd.to_numeric(part1_df.iloc[:, 7], errors='coerce'),
        'black_alone': pd.to_numeric(part1_df.iloc[:, 8], errors='coerce'),
        'aian_alone': pd.to_numeric(part1_df.iloc[:, 9], errors='coerce'),
        'asian_alone': pd.to_numeric(part1_df.iloc[:, 10], errors='coerce'),
        'nhpi_alone': pd.to_numeric(part1_df.iloc[:, 11], errors='coerce'),
        'other_alone': pd.to_numeric(part1_df.iloc[:, 12], errors='coerce'),
        'hispanic': pd.to_numeric(part1_df.iloc[:, 73], errors='coerce')
    })
    
    # Add geographic identifiers
    demographics['GEOID'] = geo_df.iloc[:, 9]  # Tract identifier
    demographics['County'] = geo_df.iloc[:, 14].astype(str).str.strip()
    demographics['BeforeCounty'] = geo_df.iloc[:, 88]
    demographics['AfterCounty'] = geo_df.iloc[:, 90]
    
    # Calculate derived demographic fields
    demographics['white_nh'] = demographics['white_alone'] - demographics['hispanic']
    
    # Determine dominant racial/ethnic group
    race_cols = ['white_nh', 'black_alone', 'aian_alone', 'asian_alone',
                 'nhpi_alone', 'other_alone', 'hispanic']
    demographics['dominant_race'] = demographics[race_cols].idxmax(axis=1)
    
    return demographics


def create_racial_map(gdf: gpd.GeoDataFrame,
                     demographics: pd.DataFrame,
                     output_path: str,
                     county_name: str) -> gpd.GeoDataFrame:
    """
    Create and save a choropleth map showing dominant racial/ethnic group by tract.
    
    Args:
        gdf: GeoDataFrame containing tract geometries
        demographics: DataFrame containing demographic data
        output_path: Path where output map should be saved
        county_name: Name of county for map title
        
    Returns:
        GeoDataFrame containing merged geometry and demographic data
    """
    print("Creating demographic map...")
    
    # Merge geometric and demographic data
    merged_gdf = gdf.merge(demographics, on='GEOID', how='left')
    
    # Handle missing data
    merged_gdf['dominant_race'] = merged_gdf['dominant_race'].fillna('Unknown')
    
    # Define color scheme for racial/ethnic groups
    color_scheme = {
        'white_nh': '#FFB6C1',    # Light pink
        'black_alone': '#87CEEB',  # Sky blue
        'asian_alone': '#98FB98',  # Pale green
        'hispanic': '#DDA0DD',     # Plum
        'aian_alone': '#F0E68C',   # Khaki
        'nhpi_alone': '#FFA07A',   # Light salmon
        'other_alone': '#D3D3D3',  # Light gray
        'Unknown': '#FFFFFF'       # White
    }

    # Create visualization
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Create the main plot
    merged_gdf.plot(
        column='dominant_race',
        categorical=True,
        legend=False,  # Disable default legend
        color=[color_scheme[race] for race in merged_gdf['dominant_race']],
        ax=ax
    )

    # Create custom legend with descriptive labels
    legend_labels = {
        'white_nh': 'White (Non-Hispanic)',
        'black_alone': 'Black/African American',
        'asian_alone': 'Asian',
        'hispanic': 'Hispanic/Latino',
        'aian_alone': 'American Indian/Alaska Native',
        'nhpi_alone': 'Native Hawaiian/Pacific Islander',
        'other_alone': 'Other Race',
        'Unknown': 'Unknown'
    }

    # Add legend patches
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color_scheme[key], 
                           label=legend_labels[key]) 
                      for key in color_scheme.keys()]
    
    ax.legend(handles=legend_elements, 
             title='Dominant Race/Ethnicity',
             bbox_to_anchor=(1.1, 0.95),
             loc='upper left')
    plt.title(f'Dominant Race/Ethnicity by Census Tract - {county_name} County (2020)')
    plt.axis('off')
    
    # Save outputs
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save unmatched records for QA
    unmatched = merged_gdf[merged_gdf['dominant_race'] == 'Unknown']
    if len(unmatched) > 0:
        unmatched[['GEOID', 'dominant_race']].to_csv('unmatched_tracts.csv', index=False)
    
    return merged_gdf


# Download tract geometries
tx_tracts = get_tracts('48')  # Texas
mi_tracts = get_tracts('26')  # Michigan

# Process demographic data
demo_mi = read_pl_data('mi2020.pl/migeo2020.pl', 'mi2020.pl/mi000012020.pl')
demo_tx = read_pl_data('tx2020.pl/txgeo2020.pl', 'tx2020.pl/tx000012020.pl')

# Filter to specific counties
wayne_tracts = mi_tracts[mi_tracts['COUNTYFP']=='163']  # Wayne County, MI
travis_tracts = tx_tracts[tx_tracts['COUNTYFP']=='453'] # Travis County, TX

create_racial_map(wayne_tracts, demo_mi, 'output/ouwayne_map.png', 'Wayne')
create_racial_map(travis_tracts, demo_tx, 'output/travis_map.png', 'Travis')
