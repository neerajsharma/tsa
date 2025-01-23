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


def create_opportunity_map(df: gpd.GeoDataFrame, city_name: str, output_path:str) -> None:
    """
    Create and save a choropleth map showing opportunity rankings by census tract.
    
    Args:
        df: GeoDataFrame containing tract geometries and opportunity rankings
        city_name: Name of city for map title
    """
    # Define color scheme for opportunity rankings
    color_scheme = {
        1: '#2ecc71',  # High opportunity - Green
        2: '#f1c40f',  # Medium opportunity - Yellow 
        3: '#e74c3c'   # Low opportunity - Red
    }
    
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Create the main plot
    df.plot(
        column='COMP_RANK',
        categorical=True,
        legend=False,
        color=[color_scheme.get(rank, '#FFFFFF') for rank in df['COMP_RANK']],
        edgecolor='0.8',
        linewidth=0.8,
        ax=ax
    )

    # Create custom legend with descriptive labels
    legend_labels = {
        1: 'High Opportunity Area',
        2: 'Medium Opportunity Area', 
        3: 'Low Opportunity Area'
    }

    # Add legend patches
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color_scheme[key],
                           label=legend_labels[key])
                      for key in sorted(color_scheme.keys())]
    
    ax.legend(handles=legend_elements,
             title='Opportunity Rankings',
             bbox_to_anchor=(1.1, 0.95),
             loc='upper left')

    plt.title(f'Opportunity Rankings by Census Tract - {city_name} (2020)')
    plt.axis('off')
    plt.tight_layout()
    plt.show()
    # Save outputs
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

def merge_geo_roi(roi: pd.DataFrame, geo: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Merge ROI (Regions of Interest) data with geographic tract data.
    
    Args:
        roi: DataFrame containing ROI data with FIPS codes
        geo: GeoDataFrame containing census tract geometries
        
    Returns:
        GeoDataFrame with merged ROI and geographic data
    """
    roi['FIPS'] = roi['FIPS'].astype(str)
    geo['GEOID'] = geo['GEOID'].astype(str)
    return geo.merge(roi, left_on='GEOID', right_on='FIPS', how='left')


def process_opportunity_data(state: str, county_fips: str, roi_path: str, city_name: str) -> None:
    """
    Process and visualize opportunity data for a given city/county.
    
    Args:
        state: Two-digit FIPS code for the state
        county_fips: Three-digit FIPS code for the county
        roi_path: Path to ROI data CSV file
        city_name: Name of the city for visualization
    """
    # Get tract geometries
    tracts_gdf = get_tracts(state)
    
    # Filter to specific county
    county_tracts = tracts_gdf[tracts_gdf['COUNTYFP'] == county_fips]
    
    # Read and merge ROI data
    roi_data = pd.read_csv(roi_path)
    merged_data = merge_geo_roi(roi_data, county_tracts)
    
    # Create visualization
    create_opportunity_map(merged_data, city_name)


# Example usage
mi_tracts = get_tracts('26')  # Michigan
wayne_tracts = mi_tracts[mi_tracts['COUNTYFP']=='163']  # Wayne County
roi_detroit = pd.read_csv('data/roi/detroit_roi.csv')
merged_detroit = merge_geo_roi(roi_detroit, wayne_tracts)
create_opportunity_map(merged_detroit, 'Detroit', 'output/detroit_opportunity.png')

# Uncomment for Austin analysis
#process_opportunity_data('48', '453', 'roi_austin/austin_roi.csv', 'Austin')