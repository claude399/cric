from bs4 import BeautifulSoup
import requests
import re
import json
from datetime import datetime

html = requests.get("https://crichd.su").text
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
        match_time_str = time_element.text.strip().split('\n')[0]  # Extract "16th Mar 01:00"
        match_time_str = re.sub(r"(\s0d)?(\s0h)?(\s0m)?$", "", match_time_str).strip()
        match_time_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", match_time_str)
        
        # Convert to datetime object (assuming match times are in the current year)
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
        
        if len(teams) == 3:
            matches.append({'time': formatted_match_time, 'team1': teams[1], 'team2': teams[2]})
    
    if matches:
        tournaments.append({'tournament': tournament_name, 'matches': matches})

# Save to JSON file
with open('matches.json', 'w', encoding='utf-8') as f:
    json.dump(tournaments, f, indent=4, ensure_ascii=False)


