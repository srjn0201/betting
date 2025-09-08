import sys
import os
import random
from datetime import datetime, timedelta

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import sessionmaker
from app.database import engine
from app.models import Team, Player, Fixture, BallByBallEvent, OddsSnapshot

Session = sessionmaker(bind=engine)
session = Session()

# --- Data Definitions ---

TEAMS = {
    "India": ["Rohit Sharma", "KL Rahul", "Virat Kohli", "Suryakumar Yadav", "Rishabh Pant", "Hardik Pandya", "Ravindra Jadeja", "Bhuvneshwar Kumar", "Mohammed Shami", "Jasprit Bumrah", "Yuzvendra Chahal"],
    "Pakistan": ["Babar Azam", "Mohammad Rizwan", "Fakhar Zaman", "Iftikhar Ahmed", "Khushdil Shah", "Asif Ali", "Shadab Khan", "Mohammad Nawaz", "Haris Rauf", "Naseem Shah", "Shaheen Afridi"]
}

# --- Helper Functions ---

def clear_data():
    print("Clearing old mock match data...")
    session.query(OddsSnapshot).delete()
    session.query(BallByBallEvent).delete()
    session.query(Fixture).delete()
    session.query(Player).delete()
    session.query(Team).delete()
    session.commit()

def create_teams_and_players():
    print("Creating teams and players...")
    teams = {}
    players = {"India": [], "Pakistan": []}
    for team_name, player_list in TEAMS.items():
        team = Team(name=team_name, short_code=team_name[:3].upper())
        session.add(team)
        session.flush() # Get team ID
        teams[team_name] = team
        for player_name in player_list:
            player = Player(name=player_name, role="All-rounder", team_id=team.id)
            session.add(player)
            players[team_name].append(player)
    session.commit()
    print("Teams and players created.")
    return teams, players

def create_upcoming_fixtures(teams):
    print("Creating upcoming fixtures...")
    team_list = list(teams.values())
    for i in range(15):
        team1, team2 = random.sample(team_list, 2)
        fixture = Fixture(
            team1_id=team1.id,
            team2_id=team2.id,
            match_date=datetime.now() + timedelta(days=i + 1),
            status="Upcoming"
        )
        session.add(fixture)
    session.commit()
    print("Upcoming fixtures created.")

def generate_realistic_odds(game_state):
    # Simplified logic: odds change based on runs and wickets
    base_rate = 1.98 - (game_state['score'] * 0.005) + (game_state['wickets'] * 0.1)
    return {
        "exchange_market": {
            "match_odds": [
                {"team": "Team A", "back": round(base_rate, 2), "lay": round(base_rate + 0.02, 2)},
                {"team": "Team B", "back": round(2.0 - base_rate + 0.04, 2), "lay": round(2.0 - base_rate + 0.06, 2)}
            ]
        },
        "fancy_markets": [{"name": "Fall of 1st Wicket", "back": 1.85, "lay": 1.95}],
        "session_markets": [{"name": "6 Over Runs", "runs": game_state['score'] + random.randint(15, 25), "back": 1.9, "lay": 1.9}]
    }

def simulate_match(teams, players):
    print("Simulating main T20 match...")
    team1 = teams["India"]
    team2 = teams["Pakistan"]
    
    fixture = Fixture(team1_id=team1.id, team2_id=team2.id, match_date=datetime.now(), status="Finished")
    session.add(fixture)
    session.commit()

    for inning in [1, 2]:
        print(f"Simulating Inning {inning}...")
        # --- FIX: Reset match state for each inning ---
        game_state = {"score": 0, "wickets": 0}
        batsman_idx, bowler_idx = 0, 5
        
        batting_team_players = players["India"] if inning == 1 else players["Pakistan"]
        bowling_team_players = players["Pakistan"] if inning == 1 else players["India"]

        for over in range(20):
            for ball in range(1, 7):
                # --- FIX: Boundary check before accessing list ---
                if game_state["wickets"] >= 10 or batsman_idx >= len(batting_team_players):
                    break

                batsman = batting_team_players[batsman_idx]
                bowler = bowling_team_players[bowler_idx]

                outcome = random.choices([0, 1, 2, 3, 4, 6, "W"], weights=[0.3, 0.3, 0.1, 0.05, 0.1, 0.05, 0.1], k=1)[0]
                
                is_wicket = outcome == "W"
                runs = 0 if is_wicket else outcome
                game_state["score"] += runs
                
                commentary = f"{batsman.name} to {bowler.name}, {runs} runs."
                if is_wicket:
                    commentary = f"OUT! {bowler.name} gets {batsman.name}!"
                    game_state["wickets"] += 1
                    batsman_idx += 1

                event = BallByBallEvent(
                    fixture_id=fixture.id, inning=inning, over=over, ball=ball,
                    batsman_id=batsman.id, bowler_id=bowler.id,
                    runs_scored=runs, is_wicket=is_wicket, commentary_text=commentary
                )
                session.add(event)
                session.flush() # Get event ID

                odds_data = generate_realistic_odds(game_state)
                snapshot = OddsSnapshot(ball_by_ball_event_id=event.id, odds_data=odds_data)
                session.add(snapshot)
            
            bowler_idx = (bowler_idx % 5) + 6  # Cycle through bowlers 6-10
            if game_state["wickets"] >= 10:
                break
        
        session.commit()
    print("Match simulation complete.")

# --- Main Execution ---

if __name__ == "__main__":
    try:
        clear_data()
        created_teams, created_players = create_teams_and_players()
        create_upcoming_fixtures(created_teams)
        simulate_match(created_teams, created_players)
        print("Mock data seeding finished successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()