import psycopg2
from typing import List, Dict, Any


class DatabaseService:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="your_db",
            user="your_user",
            password="your_password",
            host="localhost",
            port="5432"
        )
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            years_experience INT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            user_id INT REFERENCES users(id),
            skill TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INT REFERENCES users(id),
            description TEXT
        );
        """)

        self.conn.commit()
        cursor.close()

    def store_user_profile(
        self,
        name: str,
        email: str,
        years_experience: int,
        skills: List[str],
        achievements: List[str],
    ) -> int:

        cursor = self.conn.cursor()

        cursor.execute(
            "INSERT INTO users (name, email, years_experience) VALUES (%s, %s, %s) RETURNING id;",
            (name, email, years_experience),
        )

        user_id = cursor.fetchone()[0]

        for skill in skills:
            cursor.execute(
                "INSERT INTO skills (user_id, skill) VALUES (%s, %s);",
                (user_id, skill),
            )

        for achievement in achievements:
            cursor.execute(
                "INSERT INTO achievements (user_id, description) VALUES (%s, %s);",
                (user_id, achievement),
            )

        self.conn.commit()
        cursor.close()

        return user_id

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        cursor = self.conn.cursor()

        cursor.execute("SELECT name, email, years_experience FROM users WHERE id = %s;", (user_id,))
        user = cursor.fetchone()

        cursor.execute("SELECT skill FROM skills WHERE user_id = %s;", (user_id,))
        skills = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT description FROM achievements WHERE user_id = %s;", (user_id,))
        achievements = [row[0] for row in cursor.fetchall()]

        cursor.close()

        return {
            "name": user[0],
            "email": user[1],
            "years_experience": user[2],
            "skills": skills,
            "achievements": achievements,
        }