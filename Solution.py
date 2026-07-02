from typing import List, Tuple
from psycopg2 import sql
from datetime import date, datetime
import Utility.DBConnector as Connector
from Utility.ReturnValue import ReturnValue
from Utility.Exceptions import DatabaseException
from Business.Customer import Customer, BadCustomer
from Business.Order import Order, BadOrder
from Business.Dish import Dish, BadDish
from Business.OrderDish import OrderDish


# ---------------------------------- CRUD API: ----------------------------------
# Basic database functions


def create_tables():
    conn = None
    try:
        conn = Connector.DBConnector()

        queries = [

            """
            CREATE TABLE IF NOT EXISTS customers (
                cust_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT NOT NULL,

                CHECK (cust_id > 0),
                CHECK (age BETWEEN 18 AND 120),
                CHECK (CHAR_LENGTH(phone) = 10)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY,
                date TIMESTAMP(0) WITHOUT TIME ZONE NOT NULL,
                delivery_fee NUMERIC NOT NULL,
                delivery_address TEXT NOT NULL,
                tip NUMERIC NOT NULL,

                CHECK (order_id > 0),
                CHECK (delivery_fee >= 0),
                CHECK (CHAR_LENGTH(delivery_address) >= 5),
                CHECK (tip >= 0)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS dishes (
                dish_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC NOT NULL,
                is_active BOOLEAN NOT NULL,

                CHECK (dish_id > 0),
                CHECK (price > 0),
                CHECK (CHAR_LENGTH(name) >= 4)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS customer_orders (
                cust_id INTEGER NOT NULL,
                order_id INTEGER PRIMARY KEY,

                FOREIGN KEY (cust_id)
                    REFERENCES customers(cust_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
                    ON DELETE CASCADE
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_id INTEGER NOT NULL,
                dish_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                price_at_order NUMERIC NOT NULL,

                PRIMARY KEY (order_id, dish_id),

                FOREIGN KEY (order_id)
                    REFERENCES orders(order_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (dish_id)
                    REFERENCES dishes(dish_id),

                CHECK (amount >= 0),
                CHECK (price_at_order > 0)
            );
            """,

            """
            CREATE TABLE IF NOT EXISTS ratings (
                cust_id INTEGER NOT NULL,
                dish_id INTEGER NOT NULL,
                rating INTEGER NOT NULL,

                PRIMARY KEY (cust_id, dish_id),

                FOREIGN KEY (cust_id)
                    REFERENCES customers(cust_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (dish_id)
                    REFERENCES dishes(dish_id),

                CHECK (rating BETWEEN 1 AND 5)
            );
            """,

            """
            CREATE OR REPLACE VIEW order_total_view AS
            SELECT
                o.order_id,
                co.cust_id,
                o.delivery_fee
                + o.tip
                + COALESCE(SUM(oi.amount * oi.price_at_order), 0) AS total_price
            FROM orders o
            LEFT JOIN order_items oi
                ON o.order_id = oi.order_id
            LEFT JOIN customer_orders co
                ON o.order_id = co.order_id
            GROUP BY
                o.order_id,
                co.cust_id,
                o.delivery_fee,
                o.tip;
            """
        ]

        for query in queries:
            conn.execute(query)

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()

    finally:
        if conn is not None:
            conn.close()


def clear_tables():
    conn = None
    try:
        conn = Connector.DBConnector()

        queries = [
            "DELETE FROM ratings;",
            "DELETE FROM order_items;",
            "DELETE FROM customer_orders;",
            "DELETE FROM orders;",
            "DELETE FROM dishes;",
            "DELETE FROM customers;"
        ]

        for query in queries:
            conn.execute(query)

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()

    finally:
        if conn is not None:
            conn.close()


def drop_tables():
    conn = None
    try:
        conn = Connector.DBConnector()

        queries = [
            "DROP VIEW IF EXISTS order_total_view;",
            "DROP TABLE IF EXISTS ratings;",
            "DROP TABLE IF EXISTS order_items;",
            "DROP TABLE IF EXISTS customer_orders;",
            "DROP TABLE IF EXISTS orders;",
            "DROP TABLE IF EXISTS dishes;",
            "DROP TABLE IF EXISTS customers;"
        ]

        for query in queries:
            conn.execute(query)

        conn.commit()

    except Exception:
        if conn is not None:
            conn.rollback()

    finally:
        if conn is not None:
            conn.close()

# CRUD API

def add_customer(customer: Customer) -> ReturnValue:
    # TODO: implement
    pass


def get_customer(customer_id: int) -> Customer:
    # TODO: implement
    pass


def delete_customer(customer_id: int) -> ReturnValue:
    # TODO: implement
    pass


def add_order(order: Order) -> ReturnValue:
    # TODO: implement
    pass


def get_order(order_id: int) -> Order:
    # TODO: implement
    pass


def delete_order(order_id: int) -> ReturnValue:
    # TODO: implement
    pass


def add_dish(dish: Dish) -> ReturnValue:
    # TODO: implement
    pass


def get_dish(dish_id: int) -> Dish:
    # TODO: implement
    pass


def update_dish_price(dish_id: int, price: float) -> ReturnValue:
    # TODO: implement
    pass


def update_dish_active_status(dish_id: int, is_active: bool) -> ReturnValue:
    # TODO: implement
    pass


def customer_placed_order(customer_id: int, order_id: int) -> ReturnValue:
    # TODO: implement
    pass


def get_customer_that_placed_order(order_id: int) -> Customer:
    # TODO: implement
    pass


def order_contains_dish(order_id: int, dish_id: int, amount: int) -> ReturnValue:
    # TODO: implement
    pass


def order_does_not_contain_dish(order_id: int, dish_id: int) -> ReturnValue:
    # TODO: implement
    pass


def get_all_order_items(order_id: int) -> List[OrderDish]:
    # TODO: implement
    pass


def customer_rated_dish(cust_id: int, dish_id: int, rating: int) -> ReturnValue:
    # TODO: implement
    pass


def customer_deleted_rating_on_dish(cust_id: int, dish_id: int) -> ReturnValue:
    # TODO: implement
    pass

def get_all_customer_ratings(cust_id: int) -> List[Tuple[int, int]]:
    # TODO: implement
    pass
# ---------------------------------- BASIC API: ----------------------------------

# Basic API


def get_order_total_price(order_id: int) -> float:
    # TODO: implement
    pass


def get_customers_spent_max_avg_amount_money() -> List[int]:
    # TODO: implement
    pass


def get_most_profitable_dish_in_period(start: datetime, end: datetime) -> Dish:
    # TODO: implement
    pass

def did_customer_order_top_rated_dishes(cust_id: int) -> bool:
    # TODO: implement
    pass


# ---------------------------------- ADVANCED API: ----------------------------------

# Advanced API


def get_customers_rated_but_not_ordered() -> List[int]:
    # TODO: implement
    pass


def get_non_worth_price_increase() -> List[int]:
    # TODO: implement
    pass


def get_cumulative_profit_per_month(year: int) -> List[Tuple[int, float]]:
    # TODO: implement
    pass


def get_potential_dish_recommendations(cust_id: int) -> List[int]:
    # TODO: implement
    pass
