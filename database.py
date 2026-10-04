"""
Cheer Stunts Database Management (SQLite)
"""
import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cheer_stunts.db")

SAMPLE_ATHLETES = [
    # Flyers (Heights roughly 58" - 62", 4'10" to 5'2")
    {
        "name": "Lily Taylor",
        "primary_role": "Flyer",
        "secondary_roles": "",
        "height_inches": 59.0, # 4'11"
        "skill_level": 5,
        "is_active": 1,
        "notes": "Captain, elite flexibility and body control. Full-up certified."
    },
    {
        "name": "Mia Chen",
        "primary_role": "Flyer",
        "secondary_roles": "",
        "height_inches": 60.0, # 5'0"
        "skill_level": 4,
        "notes": "Solid heel stretch and arabesque. Great flyer timing."
    },
    {
        "name": "Chloe Vance",
        "primary_role": "Flyer",
        "secondary_roles": "Front Spot",
        "height_inches": 61.0, # 5'1"
        "skill_level": 3,
        "notes": "Working on spinning stunts and basket tosses."
    },
    {
        "name": "Emma Watson",
        "primary_role": "Flyer",
        "secondary_roles": "",
        "height_inches": 62.0, # 5'2"
        "skill_level": 2,
        "notes": "Developing flyer, confident in preps and extensions."
    },
    # Bases - Main Bases and Side Bases (Heights roughly 63" - 67", 5'3" to 5'7")
    {
        "name": "Sarah Miller",
        "primary_role": "Main Base",
        "secondary_roles": "Side Base",
        "height_inches": 64.0, # 5'4"
        "skill_level": 4,
        "notes": "Powerful main base grip, rock-solid locked arms."
    },
    {
        "name": "Ashley Brooks",
        "primary_role": "Side Base",
        "secondary_roles": "Main Base",
        "height_inches": 64.5, # 5'4.5"
        "skill_level": 4,
        "notes": "Great wrist control, pairs well with Sarah."
    },
    {
        "name": "Brianna Scott",
        "primary_role": "Main Base",
        "secondary_roles": "Side Base",
        "height_inches": 63.5, # 5'3.5"
        "skill_level": 3,
        "notes": "Fast dip tempo and clean foot placement."
    },
    {
        "name": "Hannah Adams",
        "primary_role": "Side Base",
        "secondary_roles": "Main Base",
        "height_inches": 63.0, # 5'3"
        "skill_level": 3,
        "notes": "Strong under-toe grip and stability."
    },
    {
        "name": "Jessica Davis",
        "primary_role": "Main Base",
        "secondary_roles": "Side Base",
        "height_inches": 65.0, # 5'5"
        "skill_level": 3,
        "notes": "Very consistent catch on basket tosses."
    },
    {
        "name": "Emily Johnson",
        "primary_role": "Side Base",
        "secondary_roles": "Main Base",
        "height_inches": 65.5, # 5'5.5"
        "skill_level": 3,
        "notes": "Pairs cleanly with Jessica for level grips."
    },
    {
        "name": "Taylor Swift",
        "primary_role": "Main Base",
        "secondary_roles": "Side Base",
        "height_inches": 66.0, # 5'6"
        "skill_level": 5,
        "notes": "Veteran base, can handle high tosses and single-leg stunts."
    },
    {
        "name": "Morgan Riley",
        "primary_role": "Side Base",
        "secondary_roles": "Main Base",
        "height_inches": 66.0, # 5'6"
        "skill_level": 4,
        "notes": "Perfect height match with Taylor, dependable balance."
    },
    {
        "name": "Olivia Martinez",
        "primary_role": "Main Base",
        "secondary_roles": "Side Base, Backspot",
        "height_inches": 65.0, # 5'5"
        "skill_level": 2,
        "notes": "Quick learner, enthusiastic base."
    },
    # Backspots (Heights roughly 67" - 71", 5'7" to 5'11" - need to be taller than bases!)
    {
        "name": "Kelsey Reed",
        "primary_role": "Backspot",
        "secondary_roles": "",
        "height_inches": 69.5, # 5'9.5"
        "skill_level": 5,
        "notes": "Senior stunt captain, calls counts, catches high tosses."
    },
    {
        "name": "Jordan Bell",
        "primary_role": "Backspot",
        "secondary_roles": "",
        "height_inches": 68.0, # 5'8"
        "skill_level": 4,
        "notes": "Strong ankle pulls and cradle catches."
    },
    {
        "name": "Sydney Green",
        "primary_role": "Backspot",
        "secondary_roles": "",
        "height_inches": 70.0, # 5'10"
        "skill_level": 4,
        "notes": "Tall reach, great coverage on twisting stunts."
    },
    {
        "name": "Avery Morgan",
        "primary_role": "Backspot",
        "secondary_roles": "Main Base",
        "height_inches": 67.5, # 5'7.5"
        "skill_level": 3,
        "notes": "Very vocal leader on floor, clean timing."
    },
    {
        "name": "Samantha Lee",
        "primary_role": "Backspot",
        "secondary_roles": "Side Base",
        "height_inches": 68.5, # 5'8.5"
        "skill_level": 2,
        "notes": "Developing backspot, great athletic instincts."
    },
    # Front Spots / Flexible Utility (Heights roughly 62" - 65")
    {
        "name": "Harper King",
        "primary_role": "Front Spot",
        "secondary_roles": "Side Base",
        "height_inches": 64.0, # 5'4"
        "skill_level": 3,
        "notes": "Great wrist support on difficult pyramids and new stunts."
    },
    {
        "name": "Zoe Bennett",
        "primary_role": "Front Spot",
        "secondary_roles": "Main Base",
        "height_inches": 63.5, # 5'3.5"
        "skill_level": 3,
        "notes": "Provides extra push on release moves."
    }
]

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(force_reset: bool = False):
    conn = get_connection()
    cursor = conn.cursor()
    
    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS athletes")
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS athletes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            primary_role TEXT NOT NULL,
            secondary_roles TEXT DEFAULT '',
            height_inches REAL NOT NULL,
            skill_level INTEGER NOT NULL CHECK(skill_level BETWEEN 1 AND 5),
            is_active INTEGER DEFAULT 1,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Check if empty
    cursor.execute("SELECT COUNT(*) as count FROM athletes")
    count = cursor.fetchone()["count"]
    if count == 0:
        for athlete in SAMPLE_ATHLETES:
            cursor.execute("""
                INSERT INTO athletes (name, primary_role, secondary_roles, height_inches, skill_level, is_active, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                athlete["name"],
                athlete["primary_role"],
                athlete.get("secondary_roles", ""),
                athlete["height_inches"],
                athlete["skill_level"],
                athlete.get("is_active", 1),
                athlete.get("notes", "")
            ))
            
    conn.commit()
    conn.close()

def get_all_athletes() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM athletes ORDER BY primary_role, name")
    rows = cursor.fetchall()
    athletes = [dict(row) for row in rows]
    conn.close()
    return athletes

def get_athlete(athlete_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_athlete(data: Dict[str, Any]) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO athletes (name, primary_role, secondary_roles, height_inches, skill_level, is_active, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name", "").strip(),
        data.get("primary_role", "").strip(),
        data.get("secondary_roles", "").strip(),
        float(data.get("height_inches", 64.0)),
        int(data.get("skill_level", 3)),
        int(data.get("is_active", 1)),
        data.get("notes", "").strip()
    ))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return get_athlete(new_id)

def update_athlete(athlete_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE athletes
        SET name = ?,
            primary_role = ?,
            secondary_roles = ?,
            height_inches = ?,
            skill_level = ?,
            is_active = ?,
            notes = ?
        WHERE id = ?
    """, (
        data.get("name", "").strip(),
        data.get("primary_role", "").strip(),
        data.get("secondary_roles", "").strip(),
        float(data.get("height_inches", 64.0)),
        int(data.get("skill_level", 3)),
        int(data.get("is_active", 1)),
        data.get("notes", "").strip(),
        athlete_id
    ))
    conn.commit()
    conn.close()
    return get_athlete(athlete_id)

def delete_athlete(athlete_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

if __name__ == "__main__":
    init_db(force_reset=True)
    all_ath = get_all_athletes()
    print(f"Initialized database with {len(all_ath)} athletes.")
