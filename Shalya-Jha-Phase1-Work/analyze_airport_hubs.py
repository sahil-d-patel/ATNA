#!/usr/bin/env python3
"""
Airport Hub Analysis Script

Analyzes flight data to identify major airport hubs by total throughput
(departures + arrivals). Outputs a ranked list of airports sorted by
flight volume.
"""

import pandas as pd
import sys
from pathlib import Path


def load_flight_data(filepath):
    """Load and parse flight reporting data."""
    print(f"Loading flight data from {filepath}...")
    
    df = pd.read_csv(
        filepath,
        usecols=['ORIGIN_AIRPORT_ID', 'ORIGIN', 'DEST_AIRPORT_ID', 'FLIGHTS'],
        dtype={
            'ORIGIN_AIRPORT_ID': int,
            'ORIGIN': str,
            'DEST_AIRPORT_ID': int,
            'FLIGHTS': float
        }
    )
    
    print(f"Loaded {len(df):,} flight records")
    return df


def load_airport_metadata(filepath):
    """Load airport master data with names and locations."""
    print(f"Loading airport metadata from {filepath}...")
    
    df = pd.read_csv(
        filepath,
        usecols=[
            'AIRPORT_ID', 
            'DISPLAY_AIRPORT_NAME', 
            'DISPLAY_AIRPORT_CITY_NAME_FULL',
            'AIRPORT_IS_LATEST'
        ],
        dtype={
            'AIRPORT_ID': int,
            'DISPLAY_AIRPORT_NAME': str,
            'DISPLAY_AIRPORT_CITY_NAME_FULL': str,
            'AIRPORT_IS_LATEST': int
        }
    )
    
    latest_airports = df[df['AIRPORT_IS_LATEST'] == 1].copy()
    latest_airports = latest_airports.drop(columns=['AIRPORT_IS_LATEST'])
    
    print(f"Loaded {len(latest_airports):,} current airports")
    return latest_airports


def calculate_hub_metrics(flight_df):
    """Calculate departure and arrival counts for each airport."""
    print("\nCalculating hub metrics...")
    
    airport_codes = flight_df[['ORIGIN_AIRPORT_ID', 'ORIGIN']].drop_duplicates()
    airport_codes.columns = ['AIRPORT_ID', 'AIRPORT_CODE']
    
    departures = flight_df.groupby('ORIGIN_AIRPORT_ID')['FLIGHTS'].sum().reset_index()
    departures.columns = ['AIRPORT_ID', 'DEPARTURES']
    
    arrivals = flight_df.groupby('DEST_AIRPORT_ID')['FLIGHTS'].sum().reset_index()
    arrivals.columns = ['AIRPORT_ID', 'ARRIVALS']
    
    combined = pd.merge(
        departures, 
        arrivals, 
        on='AIRPORT_ID', 
        how='outer'
    ).fillna(0)
    
    combined = pd.merge(
        combined,
        airport_codes,
        on='AIRPORT_ID',
        how='left'
    )
    
    combined['AIRPORT_CODE'] = combined['AIRPORT_CODE'].fillna('UNK')
    combined['DEPARTURES'] = combined['DEPARTURES'].astype(int)
    combined['ARRIVALS'] = combined['ARRIVALS'].astype(int)
    combined['TOTAL_THROUGHPUT'] = combined['DEPARTURES'] + combined['ARRIVALS']
    
    combined = combined.sort_values('TOTAL_THROUGHPUT', ascending=False).reset_index(drop=True)
    combined['RANK'] = range(1, len(combined) + 1)
    
    print(f"Analyzed {len(combined):,} unique airports")
    return combined


def enrich_with_metadata(hub_df, airport_metadata):
    """Add airport names and city information."""
    print("\nEnriching with airport metadata...")
    
    enriched = pd.merge(
        hub_df,
        airport_metadata,
        left_on='AIRPORT_ID',
        right_on='AIRPORT_ID',
        how='left'
    )
    
    enriched = enriched[[
        'RANK',
        'AIRPORT_ID',
        'AIRPORT_CODE',
        'DISPLAY_AIRPORT_NAME',
        'DISPLAY_AIRPORT_CITY_NAME_FULL',
        'DEPARTURES',
        'ARRIVALS',
        'TOTAL_THROUGHPUT'
    ]]
    
    enriched.columns = [
        'RANK',
        'AIRPORT_ID',
        'AIRPORT_CODE',
        'AIRPORT_NAME',
        'CITY',
        'DEPARTURES',
        'ARRIVALS',
        'TOTAL_THROUGHPUT'
    ]
    
    return enriched


def main():
    script_dir = Path(__file__).parent
    
    flight_data_path = script_dir / 'T_ONTIME_REPORTING.csv'
    airport_metadata_path = script_dir / 'T_MASTER_CORD.csv'
    output_path = script_dir / 'airport_hubs_ranked.csv'
    
    if not flight_data_path.exists():
        print(f"Error: Flight data file not found: {flight_data_path}")
        sys.exit(1)
    
    if not airport_metadata_path.exists():
        print(f"Error: Airport metadata file not found: {airport_metadata_path}")
        sys.exit(1)
    
    flight_df = load_flight_data(flight_data_path)
    airport_metadata = load_airport_metadata(airport_metadata_path)
    
    hub_metrics = calculate_hub_metrics(flight_df)
    
    final_results = enrich_with_metadata(hub_metrics, airport_metadata)
    
    final_results.to_csv(output_path, index=False)
    print(f"\n✓ Results saved to: {output_path}")
    
    print("\n" + "="*80)
    print("TOP 20 AIRPORT HUBS BY TOTAL THROUGHPUT")
    print("="*80)
    print(final_results.head(20).to_string(index=False))
    print("="*80)
    
    print(f"\nTotal airports analyzed: {len(final_results):,}")
    print(f"Total flights processed: {final_results['TOTAL_THROUGHPUT'].sum():,.0f}")


if __name__ == '__main__':
    main()
