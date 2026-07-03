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


def create_tables() -> None:
    conn = None
    try:
        conn = Connector.DBConnector()
        # Create tables

        # Customers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Customers (
                cust_id INT PRIMARY KEY CHECK (cust_id > 0),
                full_name VARCHAR NOT NULL,
                age INT NOT NULL CHECK (age >= 18 and age <= 120),
                phone CHAR(10) NOT NULL CHECK (LENGTH(phone) = 10)
            );
        """)

        # Orders table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Orders (
                order_id INT PRIMARY KEY CHECK (order_id > 0),
                date TIMESTAMP(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                delivery_fee DECIMAL NOT NULL CHECK (delivery_fee >= 0),
                delivery_address VARCHAR NOT NULL CHECK (LENGTH(delivery_address) >= 5),
                tip DECIMAL NOT NULL CHECK (tip >= 0),
                customer_id INT REFERENCES Customers(cust_id) ON DELETE SET NULL
            );
        """)

        # Dishes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Dishes (
                dish_id INT PRIMARY KEY CHECK (dish_id > 0),
                name VARCHAR NOT NULL CHECK (LENGTH(name) >= 4),
                price DECIMAL NOT NULL CHECK (price > 0),
                is_active BOOLEAN NOT NULL
            );
        """)

        # OrderDishes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS OrderDishes (
                order_id INT REFERENCES Orders(order_id) ON DELETE CASCADE,
                dish_id INT REFERENCES Dishes(dish_id),
                amount INT NOT NULL CHECK (amount >= 0),
                price_of_order DECIMAL NOT NULL,
                PRIMARY KEY (order_id, dish_id)
            );
        """)

        # Ratings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Ratings (
                customer_id INT REFERENCES Customers(cust_id) ON DELETE CASCADE,
                dish_id INT REFERENCES Dishes(dish_id),
                rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                PRIMARY KEY (customer_id, dish_id)
            );
        """)

        conn.execute("""
            CREATE OR REPLACE VIEW OrderTotals AS
            SELECT o.order_id,
                   o.customer_id,
                   o.delivery_fee + o.tip + COALESCE(SUM(od.price_of_order * od.amount), 0) AS total_price
            FROM Orders o
            LEFT JOIN OrderDishes od ON o.order_id = od.order_id
            GROUP BY o.order_id, o.customer_id, o.delivery_fee, o.tip;
        """)

    except DatabaseException as e:
        print(e)
    finally:
        if conn:
            conn.close()


def clear_tables() -> None:
    conn = None
    try:
        conn = Connector.DBConnector()
        conn.execute("DELETE FROM OrderDishes;")
        conn.execute("DELETE FROM Ratings;")
        conn.execute("DELETE FROM Orders;")
        conn.execute("DELETE FROM Dishes;")
        conn.execute("DELETE FROM Customers;")
    except DatabaseException as e:
        print(e)
    finally:
        if conn:
            conn.close()


def drop_tables() -> None:
    conn = None
    try:
        conn = Connector.DBConnector()
        conn.execute("DROP VIEW IF EXISTS OrderTotals CASCADE;")
        conn.execute("DROP TABLE IF EXISTS OrderDishes CASCADE;")
        conn.execute("DROP TABLE IF EXISTS Ratings CASCADE;")
        conn.execute("DROP TABLE IF EXISTS Orders CASCADE;")
        conn.execute("DROP TABLE IF EXISTS Dishes CASCADE;")
        conn.execute("DROP TABLE IF EXISTS Customers CASCADE;")
    except DatabaseException as e:
        print(e)
    finally:
        if conn:
            conn.close()


# CRUD API

def add_customer(customer: Customer) -> ReturnValue:
    # TODO: implement
    conn = None
    try :
        cust_id = customer.get_cust_id()
        full_name = customer.get_full_name()
        age = customer.get_age()
        phone = customer.get_phone()

        if cust_id is None or full_name is None or age is None or phone is None:
            return ReturnValue.BAD_PARAMS
        if cust_id <= 0 or age < 18 or age > 120 or len(phone) != 10 :
            return ReturnValue.BAD_PARAMS

        conn = Connector.DBConnector()
        conn.execute(sql.SQL("""
                INSERT INTO Customers(cust_id, full_name, age, phone)
                VALUES ({cust_id}, {full_name}, {age}, {phone});
        """).format(
            cust_id=sql.Literal(cust_id),
            full_name=sql.Literal(full_name),
            age=sql.Literal(age),
            phone=sql.Literal(phone)
        ))
        return ReturnValue.OK
    except DatabaseException as e:
        msg = str(e).lower()

        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return ReturnValue.ALREADY_EXISTS

        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()



def get_customer(customer_id: int) -> Customer:
    # TODO: implement
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT cust_id, full_name, age, phone 
                FROM Customers 
                WHERE cust_id = {}
            """).format(sql.Literal(customer_id))
        rows_affected, result = conn.execute(query)
        if rows_affected == 0:  
            return BadCustomer()

        row = result.rows[0]
        customer = Customer()
        customer.set_cust_id(row[0])
        customer.set_full_name(row[1])
        customer.set_age(row[2])
        customer.set_phone(row[3])

        return customer
    except DatabaseException as e:
        return BadCustomer()

    finally:
        if conn:
            conn.close()



def delete_customer(customer_id: int) -> ReturnValue:
    # TODO: implement
    conn = None
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
                DELETE FROM Customers 
                WHERE cust_id = {}
            """).format(sql.Literal(customer_id))

        rows_affected, _ = conn.execute(query)

        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS

        return ReturnValue.OK

    except DatabaseException as e:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def add_order(order: Order) -> ReturnValue:
    # TODO: implement
    conn = None
    try:
        order_id = order.get_order_id()
        date = order.get_datetime()
        delivery_fee = order.get_delivery_fee()
        delivery_address = order.get_delivery_address()
        tip = order.get_tip()

        if order_id is None or delivery_fee is None or delivery_address is None or tip is None:
            return ReturnValue.BAD_PARAMS
        if order_id <= 0 or tip < 0 or len(delivery_address) < 5 or delivery_fee < 0 :
            return ReturnValue.BAD_PARAMS
        conn = Connector.DBConnector()
        conn.execute(sql.SQL("""
                        INSERT INTO Orders(order_id, date, delivery_fee, delivery_address, tip)
                        VALUES ({order_id}, {date}, {delivery_fee}, {delivery_address}, {tip});
                """).format(
            order_id=sql.Literal(order_id),
            date=sql.Literal(date),
            delivery_fee=sql.Literal(delivery_fee),
            delivery_address=sql.Literal(delivery_address),
            tip=sql.Literal(tip)
        ))
        return ReturnValue.OK

    except DatabaseException as e:
        msg = str(e).lower()

        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return ReturnValue.ALREADY_EXISTS

        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def get_order(order_id: int) -> Order:
    # TODO: implement
    conn = None
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
                SELECT order_id, date, delivery_fee, delivery_address, tip
                FROM Orders
                WHERE order_id = {};
            """).format(sql.Literal(order_id))

        rows_affected, result = conn.execute(query)

        if rows_affected == 0:
            return BadOrder()

        row = result.rows[0]

        order = Order()
        order.set_order_id(row[0])
        order.set_datetime(row[1])
        order.set_delivery_fee(row[2])
        order.set_delivery_address(row[3])
        order.set_tip(row[4])

        return order

    except DatabaseException:
        return BadOrder()

    finally:
        if conn:
            conn.close()


def delete_order(order_id: int) -> ReturnValue:
    # TODO: implement
    conn = None
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
                DELETE FROM Orders
                WHERE order_id = {}
            """).format(sql.Literal(order_id))

        rows_affected, _ = conn.execute(query)

        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS

        return ReturnValue.OK

    except DatabaseException:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def add_dish(dish: Dish) -> ReturnValue:
    # TODO: implement
    conn = None
    try:
        dish_id = dish.get_dish_id()
        name = dish.get_name()
        price = dish.get_price()
        is_active = dish.get_is_active()

        # Check for null attributes
        if dish_id is None or name is None or price is None or is_active is None:
            return ReturnValue.BAD_PARAMS

        # Check constraints: dish_id positive, price positive, name length >= 4
        if dish_id <= 0 or price <= 0 or len(name) < 4:
            return ReturnValue.BAD_PARAMS

        conn = Connector.DBConnector()
        conn.execute(sql.SQL("""
                    INSERT INTO Dishes(dish_id, name, price, is_active)
                    VALUES ({dish_id}, {name}, {price}, {is_active});
            """).format(
            dish_id=sql.Literal(dish_id),
            name=sql.Literal(name),
            price=sql.Literal(price),
            is_active=sql.Literal(is_active)
        ))
        return ReturnValue.OK

    except DatabaseException as e:
        msg = str(e).lower()

        if "duplicate" in msg or "unique" in msg or "23505" in msg:
            return ReturnValue.ALREADY_EXISTS

        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def get_dish(dish_id: int) -> Dish:
    # TODO: implement
    conn = None
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
                SELECT dish_id, name, price, is_active
                FROM Dishes
                WHERE dish_id = {};
            """).format(sql.Literal(dish_id))

        rows_affected, result = conn.execute(query)

        if rows_affected == 0:
            return BadDish()

        row = result.rows[0]

        dish = Dish()
        dish.set_dish_id(row[0])
        dish.set_name(row[1])
        dish.set_price(float(row[2]))
        dish.set_is_active(row[3])

        return dish

    except DatabaseException:
        return BadDish()

    finally:
        if conn:
            conn.close()


def update_dish_price(dish_id: int, price: float) -> ReturnValue:
    conn = None
    try:
        conn = Connector.DBConnector()
        rows_affected, _ = conn.execute(sql.SQL("""
                    UPDATE Dishes
                    SET price = {price}
                    WHERE dish_id = {dish_id} AND is_active = TRUE;
            """).format(
            dish_id=sql.Literal(dish_id),
            price=sql.Literal(price)
        ))
        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS
           
        return ReturnValue.OK

    except (DatabaseException.CHECK_VIOLATION, DatabaseException.NOT_NULL_VIOLATION):
        return ReturnValue.BAD_PARAMS
    
    except DatabaseException:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()
        
        
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
