import sqlite3
import pandas as pd

from schema import JobRecord


DB_FILE = "jobs.db"
CSV_FILE = "jobs_clean.csv"


# --------------------------------------------------
# 1. Convert JobRecord objects to DataFrame
# --------------------------------------------------

def jobs_to_dataframe(jobs):

    rows = []

    for job in jobs:

        data = job.model_dump()

        # Convert skills list to text
        data["skills"] = ", ".join(data["skills"])

        rows.append(data)

    return pd.DataFrame(rows)


# --------------------------------------------------
# 2. Save jobs to SQLite
# --------------------------------------------------

def save_to_database(jobs):

    new_df = jobs_to_dataframe(jobs)

    if new_df.empty:
        return

    connection = sqlite3.connect(DB_FILE)

    # Check whether the jobs table already exists
    table_exists = pd.read_sql_query(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name='jobs'
        """,
        connection
    )

    if table_exists.empty:

        # No existing table
        new_df.to_sql(
            "jobs",
            connection,
            if_exists="replace",
            index=False
        )

    else:

        # ------------------------------------------
        # Read ALL existing database jobs
        # into a DataFrame
        # ------------------------------------------

        existing_df = pd.read_sql_query(
            "SELECT * FROM jobs",
            connection
        )

        # ------------------------------------------
        # Combine old + new
        # ------------------------------------------

        combined_df = pd.concat(
            [existing_df, new_df],
            ignore_index=True
        )

        # ------------------------------------------
        # Remove duplicates
        # ------------------------------------------

        combined_df = combined_df.drop_duplicates(
            subset=["title", "source_snippet"],
            keep="first"
        )

        # ------------------------------------------
        # Write the complete DataFrame back
        # ------------------------------------------

        combined_df.to_sql(
            "jobs",
            connection,
            if_exists="replace",
            index=False
        )

    connection.close()


# --------------------------------------------------
# 3. Save jobs to CSV
# --------------------------------------------------

def save_to_csv(jobs):

    new_df = jobs_to_dataframe(jobs)

    if new_df.empty:
        return

    try:

        # Read existing CSV
        existing_df = pd.read_csv(CSV_FILE)

        # Combine old + new
        combined_df = pd.concat(
            [existing_df, new_df],
            ignore_index=True
        )

        # Remove duplicates
        combined_df = combined_df.drop_duplicates(
            subset=["title", "source_snippet"],
            keep="first"
        )

    except FileNotFoundError:

        combined_df = new_df

    # Save final DataFrame
    combined_df.to_csv(
        CSV_FILE,
        index=False
    )


# --------------------------------------------------
# 4. Save to both database and CSV
# --------------------------------------------------

def save_jobs(jobs):

    save_to_database(jobs)

    save_to_csv(jobs)