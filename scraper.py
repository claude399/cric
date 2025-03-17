from bs4 import BeautifulSoup
import requests
import re
import json
from datetime import datetime

# Base URL
BASE_URL = "https://crichd.su"

# Headers for requests
HEADERS = {
    "referer": BASE_URL,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
}

# Fetch main page
html = requests.get(BASE_URL, headers=HEADERS).text
soup = BeautifulSoup(html, 'html.parser')

tournament_blocks = soup.find_all('div', class_='mb-7 last:mb-3')

tournaments = []

for tournament in tournament_blocks:
    # Extract tournament name
    tournament_name_div = tournament.find('div', class_='text-white font-semibold text-sm')
    if not tournament_name_div:
        continue
    tournament_name = tournament_name_div.text.strip()
    
    matches = []
    match_cards = tournament.find_all('a')
    
    for match_card in match_cards:
        # Extract match time
        time_element = match_card.find('div', class_='col-span-3').find_all('div')[-1]
        match_time_str = time_element.text.strip().split('\n')[0]
        match_time_str = re.sub(r"(\s0d)?(\s0h)?(\s0m)?$", "", match_time_str).strip()
        match_time_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", match_time_str)
        
        # Convert to datetime object
        match_time = datetime.strptime(match_time_str, "%d %b %H:%M")
        match_time = match_time.replace(year=datetime.now().year)
        
        # Calculate time difference
        current_time = datetime.now()
        time_diff = match_time - current_time
        
        # Extract days, hours, and minutes
        days = time_diff.days
        hours, remainder = divmod(time_diff.seconds, 3600)
        minutes = remainder // 60
        
        time_parts = []
        if time_diff.total_seconds() > 0:
            if days > 0:
                time_parts.append(f"{days}d")
            if hours > 0:
                time_parts.append(f"{hours}h")
            if minutes > 0:
                time_parts.append(f"{minutes}m")
        
        time_remaining = " " + " ".join(time_parts) if time_parts else ""
        formatted_match_time = f"{match_time.strftime('%d %b %H:%M')}{time_remaining}"
        
        # Extract teams
        team_elements = match_card.find_all('span')
        teams = [team.text.strip() for team in team_elements if team.text.strip()]
        
        # Extract match link
        match_link = match_card.get('href')
        full_match_url = BASE_URL + match_link if match_link else None

        # Extract channel links from match page
        channel_links = []
        if full_match_url:
            try:
                match_page_html = requests.get(full_match_url, headers=HEADERS).text
                match_soup = BeautifulSoup(match_page_html, 'html.parser')
                
                # Locate "Links:" section
                links_section = match_soup.find('span', class_='text-lg font-semibold', string='Links:')
                if links_section:
                    parent_div = links_section.find_parent('div')
                    if parent_div:
                        links = parent_div.find_all('a')
                        channel_links = [BASE_URL + link.get('href') for link in links if link.get('href')]

            except Exception as e:
                print(f"Error fetching {full_match_url}: {e}")

        # Extract iframe sources from each channel link
        iframe_sources = []
        extracted_data = []  # To store fid, v_con, v_dt, and constructed URLs

        for channel_url in channel_links:
            try:
                channel_html = requests.get(channel_url, headers=HEADERS).text
                channel_soup = BeautifulSoup(channel_html, 'html.parser')

                # Find iframe source
                iframe = channel_soup.find('iframe')
                if iframe and iframe.get('src'):
                    iframe_src = iframe.get('src')
                    iframe_sources.append(iframe_src)

                    # Visit iframe source to extract fid, v_con, v_dt
                    try:
                        iframe_html = requests.get(iframe_src, headers=HEADERS).text
                        
                        # Extract fid
                        fid_match = re.search(r'fid="([^"]+)"', iframe_html)
                        fid = fid_match.group(1) if fid_match else None
                        
                        # Extract v_con and v_dt
                        v_con_match = re.search(r'v_con\s*=\s*"([^"]+)"', iframe_html)
                        v_dt_match = re.search(r'v_dt\s*=\s*"([^"]+)"', iframe_html)
                        v_con = v_con_match.group(1) if v_con_match else None
                        v_dt = v_dt_match.group(1) if v_dt_match else None
                        
                        # Construct final URL
                        if fid and v_con and v_dt:
                            final_url = f"https://dlolcast.com/playurn.php?v={fid}&secure={v_con}&expires={v_dt}"
                            extracted_data.append({
                                'fid': fid,
                                'v_con': v_con,
                                'v_dt': v_dt,
                                'final_url': final_url
                            })

                            # Extract stream URL from final URL
                            response = requests.get(final_url, headers={"referer": "https://cdn.crichdplays.ru/"}).text
                            response = response.replace('\\/', '/')  # Normalize URL format
                            function_match = re.search(r'function\s+([a-zA-Z0-9_]+)\s*\(\)', response)
                            if function_match:
                                function_name = function_match.group(1)
                                function_body_match = re.search(rf'function\s+{function_name}\s*\(\)\s*\{{([\s\S]*?)\}}', response)
                                if function_body_match:
                                    array_match = re.search(r'return\s*\(\[([\s\S]+?)\]\.join\(\"\"\)', function_body_match.group(1))
                                    if array_match:
                                        array_string = array_match.group(1)
                                        stream_url = "".join(re.findall(r'"(.*?)"', array_string))
                                        stream_url  = stream_url .replace("https:////", "https://")
# print(s_fixed)
                                        extracted_data[-1]['streaming_url'] = stream_url
                                        

                    except Exception as e:
                        print(f"Error fetching iframe source {iframe_src}: {e}")

            except Exception as e:
                print(f"Error fetching {channel_url}: {e}")

        if len(teams) == 3:
            matches.append({
                'time': formatted_match_time,
                'team1': teams[1],
                'team2': teams[2],
                'match_url': full_match_url,
                'channel_links': channel_links,
                'iframe_sources': iframe_sources,
                'extracted_data': extracted_data
            })
    
    if matches:
        tournaments.append({'tournament': tournament_name, 'matches': matches})

# Save to JSON file
with open('matches.json', 'w', encoding='utf-8') as f:
    json.dump(tournaments, f, indent=4, ensure_ascii=False)

