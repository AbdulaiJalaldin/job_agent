import psycopg2
from typing import Optional, List, Dict, Any

import os
from dotenv import load_dotenv

load_dotenv()


class DatabaseService:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            email TEXT,
            years_experience INT,
            additional_info TEXT,
            goals TEXT
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
        years_experience: Optional[int],
        skills: List[str],
        achievements: List[str],
    ) -> int:

        cursor = self.conn.cursor()

        try:
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

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

        return user_id

    def update_user_additional_info(
        self,
        user_id: int,
        additional_info: Optional[str],
        goals: Optional[str],
    ) -> None:
        """Update a user's additional info and goals."""
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "UPDATE users SET additional_info = %s, goals = %s WHERE id = %s;",
                (additional_info, goals, user_id),
            )
            self.conn.commit()

        except Exception:
            self.conn.rollback()
            raise

        finally:
            cursor.close()

    def get_existing_user(self) -> Optional[Dict[str, Any]]:
        """Check if a user already exists in the database.
        Returns a dict with user_id and has_additional_info, or None if no user exists.
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "SELECT id, additional_info, goals FROM users ORDER BY id DESC LIMIT 1;"
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "user_id": row[0],
                "has_additional_info": row[1] is not None and row[2] is not None,
            }

        finally:
            cursor.close()

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                "SELECT name, email, years_experience, additional_info, goals FROM users WHERE id = %s;",
                (user_id,),
            )
            user = cursor.fetchone()

            if user is None:
                raise ValueError(f"No user found with id {user_id}")

            cursor.execute(
                "SELECT skill FROM skills WHERE user_id = %s;", (user_id,)
            )
            skills = [row[0] for row in cursor.fetchall()]

            cursor.execute(
                "SELECT description FROM achievements WHERE user_id = %s;",
                (user_id,),
            )
            achievements = [row[0] for row in cursor.fetchall()]

        finally:
            cursor.close()

        return {
            "name": user[0],
            "email": user[1],
            "years_experience": user[2],
            "additional_info": user[3],
            "goals": user[4],
            "skills": skills,
            "achievements": achievements,
        }

    def close(self):
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        """Support usage as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting context manager."""
        self.close()