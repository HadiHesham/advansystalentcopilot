from mcp.server.fastmcp import FastMCP
from loguru import logger
import psycopg2
import json

mcp = FastMCP("Postgres")


def get_db_connection():
    return psycopg2.connect(
        dbname='TalentCopilot',
        user='postgres',
        password='careerHub',
        host='localhost',
        port='5432'
    )


@mcp.tool()
def insert_data(table: str, values: dict) -> str:
    """Insert a record into a table."""
    logger.info(f"Inserting into {table}: {values}")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        columns = ', '.join(values.keys())
        placeholders = ', '.join(['%s'] * len(values))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(values.values()))
        conn.commit()
        return json.dumps({"status": "success", "inserted": values})
    except Exception as e:
        logger.error(f"Insert failed: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@mcp.tool()
def select_data(table: str, columns: list, conditions: dict = {}) -> str:
    """Select specific columns from a table with optional conditions."""
    logger.info(f"Selecting from {table}: columns={columns}, conditions={conditions}")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        column_list = ', '.join(columns)
        sql = f"SELECT {column_list} FROM {table}"

        if conditions:
            where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
            sql += f" WHERE {where_clause}"
            cursor.execute(sql, list(conditions.values()))
        else:
            cursor.execute(sql)

        rows = cursor.fetchall()
        result = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rows]
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Select failed: {e}")
        return json.dumps({"error": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@mcp.tool()
def delete_data(table: str, conditions: dict) -> str:
    """Run a DELETE query on the database."""
    logger.info(f"Running DELETE query: {table} where {conditions}")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clause}"

        cursor.execute(sql, list(conditions.values()))
        conn.commit()

        return json.dumps({
            "status": "success",
            "deleted_where": conditions
        })
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@mcp.tool()
def update_data(table: str, conditions: dict, updates: dict) -> str:
    """Update records in the given table where conditions match."""
    logger.info(f"Updating {table} where {conditions} with {updates}")
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        where_clause = ' AND '.join([f"{k} = %s" for k in conditions.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        values = list(updates.values()) + list(conditions.values())
        cursor.execute(sql, values)
        conn.commit()

        return json.dumps({
            "status": "success",
            "updated_fields": updates,
            "where": conditions
        })
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        if cursor: cursor.close()
        if conn: conn.close()



if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run(transport="stdio")

