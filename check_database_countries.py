#!/usr/bin/env python3
"""
StreamGank Database Country Checker
Connects to Supabase database to check which countries have available movies
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main function to check countries in StreamGank database"""
    
    # Initialize Supabase client
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing SUPABASE_URL or SUPABASE_KEY environment variables")
            print("📝 Please check your .env file")
            return
            
        print("🔗 Connecting to Supabase database...")
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Connected to Supabase successfully")
        
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return
    
    try:
        print("\n🌍 Querying movie_localizations table for all countries...")
        
        # Query all country codes from movie_localizations table
        response = supabase.table('movie_localizations').select('country_code').execute()
        
        if response.data:
            print(f"✅ Found {len(response.data)} total movie records")
            
            # Count movies per country
            country_counts = {}
            for record in response.data:
                country_code = record.get('country_code')
                if country_code:
                    country_counts[country_code] = country_counts.get(country_code, 0) + 1
            
            # Country code to name mapping
            country_names = {
                'AT': 'Austria',
                'AU': 'Australia', 
                'BE': 'Belgium',
                'BG': 'Bulgaria',
                'BR': 'Brazil',
                'CA': 'Canada',
                'CH': 'Switzerland',
                'CZ': 'Czech Republic',
                'DE': 'Germany',
                'DK': 'Denmark',
                'EE': 'Estonia',
                'ES': 'Spain',
                'FI': 'Finland',
                'FR': 'France',
                'GB': 'United Kingdom',
                'HK': 'Hong Kong',
                'HR': 'Croatia',
                'HU': 'Hungary',
                'IE': 'Ireland',
                'IL': 'Israel',
                'IN': 'India',
                'IT': 'Italy',
                'JP': 'Japan',
                'KR': 'South Korea',
                'LT': 'Lithuania',
                'LU': 'Luxembourg',
                'LV': 'Latvia',
                'MA': 'Morocco',
                'NL': 'Netherlands',
                'NO': 'Norway',
                'NZ': 'New Zealand',
                'PL': 'Poland',
                'PT': 'Portugal',
                'RO': 'Romania',
                'SE': 'Sweden',
                'SI': 'Slovenia',
                'SK': 'Slovakia',
                'TN': 'Tunisia',
                'TR': 'Turkey',
                'UK': 'United Kingdom',
                'US': 'United States',
                'ZA': 'South Africa'
            }
            
            # Sort countries by movie count (descending)
            sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
            
            print(f"\n📊 Found movies in {len(sorted_countries)} countries:")
            print("=" * 60)
            
            # Display results
            for country_code, count in sorted_countries:
                country_name = country_names.get(country_code, f"Unknown ({country_code})")
                print(f"{country_code:3} | {country_name:20} | {count:4} movies")
            
            print("=" * 60)
            
            # Show top 10 countries
            print(f"\n🏆 Top 10 countries with most movies:")
            for i, (country_code, count) in enumerate(sorted_countries[:10], 1):
                country_name = country_names.get(country_code, f"Unknown ({country_code})")
                print(f"{i:2}. {country_name} ({country_code}): {count} movies")
            
            # Show countries with 20+ movies (good for dropdown)
            good_countries = [(code, count) for code, count in sorted_countries if count >= 20]
            print(f"\n✨ Countries with 20+ movies (recommended for dropdown): {len(good_countries)}")
            for country_code, count in good_countries:
                country_name = country_names.get(country_code, f"Unknown ({country_code})")
                print(f"   {country_name} ({country_code}): {count} movies")
            
            # Generate HTML dropdown code
            print(f"\n📝 HTML dropdown code for countries with movies:")
            print('<select id="country" class="form-select">')
            for country_code, count in sorted_countries:
                country_name = country_names.get(country_code, f"Unknown ({country_code})")
                selected = ' selected' if country_code == 'FR' else ''
                print(f'    <option value="{country_code}"{selected}>{country_name} ({country_code}) - {count} movies</option>')
            print('</select>')
            
        else:
            print("❌ No data found in movie_localizations table")
            
    except Exception as e:
        print(f"❌ Error querying database: {e}")
        return

if __name__ == "__main__":
    main()