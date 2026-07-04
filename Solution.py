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
                price_at_order DECIMAL NOT NULL,
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
        # Create view for order totals
        conn.execute("""
            CREATE OR REPLACE VIEW OrderTotals AS
            SELECT o.order_id,
                   o.customer_id,
                   o.delivery_fee + o.tip + COALESCE(SUM(od.price_at_order * od.amount), 0) AS total_price
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
    except DatabaseException.UNIQUE_VIOLATION:
        return ReturnValue.ALREADY_EXISTS

    except DatabaseException:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()



def get_customer(customer_id: int) -> Customer:
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

        row = result[0]
        customer = Customer()
        customer.set_cust_id(row['cust_id'])
        customer.set_full_name(row['full_name'])
        customer.set_age(row['age'])
        customer.set_phone(row['phone'])

        return customer
    except DatabaseException as e:
        return BadCustomer()

    finally:
        if conn:
            conn.close()



def delete_customer(customer_id: int) -> ReturnValue:
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

    except DatabaseException.UNIQUE_VIOLATION:
        return ReturnValue.ALREADY_EXISTS

    except DatabaseException:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def get_order(order_id: int) -> Order:
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

        row = result[0]

        order = Order()
        order.set_order_id(row['order_id'])
        order.set_datetime(row['date'])
        order.set_delivery_fee(row['delivery_fee'])
        order.set_delivery_address(row['delivery_address'])
        order.set_tip(row['tip'])

        return order

    except DatabaseException:
        return BadOrder()

    finally:
        if conn:
            conn.close()


def delete_order(order_id: int) -> ReturnValue:
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


    except DatabaseException.UNIQUE_VIOLATION:

        return ReturnValue.ALREADY_EXISTS


    except DatabaseException:

        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def get_dish(dish_id: int) -> Dish:
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
    conn = None
    try:
        conn = Connector.DBConnector()
        rows_affected, _ = conn.execute(sql.SQL("""
                    UPDATE Dishes
                    SET is_active = {is_active}
                    WHERE dish_id = {dish_id};
            """).format(
            dish_id=sql.Literal(dish_id),
            is_active=sql.Literal(is_active)
        ))
        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS

        return ReturnValue.OK

    except DatabaseException:
        return ReturnValue.ERROR
    finally:
        if conn:
            conn.close()


def customer_placed_order(customer_id: int, order_id: int) -> ReturnValue:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                WITH check_status AS (      
                    SELECT
                        EXISTS (SELECT 1 FROM Orders WHERE order_id = {order_id}) AS order_exists,
                        EXISTS (SELECT 1 FROM Customers WHERE cust_id = {customer_id}) AS customer_exists,
                        (SELECT customer_id FROM Orders WHERE order_id = {order_id}) as current_customer
                ),
                update_customer AS (
                    UPDATE Orders
                    SET customer_id = {customer_id}
                    WHERE order_id = {order_id} AND customer_id IS NULL
                    AND EXISTS (SELECT 1 FROM Customers WHERE cust_id = {customer_id})
                    RETURNING 1
                )
                SELECT order_exists, customer_exists, current_customer FROM check_status;                        
            """).format(
            customer_id=sql.Literal(customer_id),
            order_id=sql.Literal(order_id)
        )
        rows_affected, result = conn.execute(query)
        if result.size() == 0:
            return ReturnValue.NOT_EXISTS
        
        row = result[0]   
        if not row['order_exists'] or not row['customer_exists']:
            return ReturnValue.NOT_EXISTS
        if row['current_customer'] is not None:
            return ReturnValue.ALREADY_EXISTS
        return ReturnValue.OK
    
    except DatabaseException.FOREIGN_KEY_VIOLATION as e:
        return ReturnValue.NOT_EXISTS
    except DatabaseException:
        return ReturnValue.ERROR

    finally:
        if conn:
            conn.close()


def get_customer_that_placed_order(order_id: int) -> Customer:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT c.cust_id, c.full_name, c.age, c.phone
                FROM Customers c
                JOIN Orders o ON c.cust_id = o.customer_id
                WHERE o.order_id = {order_id};
            """).format(order_id=sql.Literal(order_id))
        
        rows_affected, result = conn.execute(query)
        if result.size() == 0:
            return BadCustomer()

        row = result[0]
        customer = Customer()
        customer.set_cust_id(row['cust_id'])
        customer.set_full_name(row['full_name'])
        customer.set_age(row['age'])
        customer.set_phone(row['phone'])

        return customer
    except DatabaseException:
        return BadCustomer()
    finally:
        if conn:
            conn.close()


def order_contains_dish(order_id: int, dish_id: int, amount: int) -> ReturnValue:
    if amount < 0:
        return ReturnValue.BAD_PARAMS
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                WITH check_status AS (
                    SELECT
                        EXISTS (SELECT 1 FROM Orders WHERE order_id = {order_id}) AS order_exists,
                        (SELECT is_active FROM Dishes WHERE dish_id = {dish_id}) AS dish_active,
                        EXISTS (SELECT 1 FROM OrderDishes WHERE order_id = {order_id} AND dish_id = {dish_id}) AS dish_already_in_order
                ),
                insert_dish AS (
                    INSERT INTO OrderDishes(order_id, dish_id, amount, price_at_order)
                    SELECT {order_id}, {dish_id}, {amount}, d.price
                    FROM Dishes d
                    WHERE d.dish_id = {dish_id} AND d.is_active = TRUE
                        AND EXISTS (SELECT 1 FROM Orders WHERE order_id = {order_id})
                        AND NOT EXISTS (SELECT 1 FROM OrderDishes WHERE order_id = {order_id} AND dish_id = {dish_id})
                    RETURNING 1
                )
                SELECT order_exists, dish_active, dish_already_in_order
                FROM check_status;
            """).format(
            order_id=sql.Literal(order_id),
            dish_id=sql.Literal(dish_id),
            amount=sql.Literal(amount)
        )
        _ , result = conn.execute(query)
        if result.size() == 0:
            return ReturnValue.NOT_EXISTS
        row = result[0]
        if row['order_exists'] is False or row['dish_active'] is not True:
            return ReturnValue.NOT_EXISTS
        if row['dish_already_in_order'] is True:
            return ReturnValue.ALREADY_EXISTS
        return ReturnValue.OK
    except DatabaseException.UNIQUE_VIOLATION:
        return ReturnValue.ALREADY_EXISTS
    except DatabaseException.FOREIGN_KEY_VIOLATION:
        return ReturnValue.NOT_EXISTS
    except DatabaseException.CHECK_VIOLATION:
        return ReturnValue.BAD_PARAMS
    except DatabaseException:
        return ReturnValue.ERROR
    finally:
        if conn:
            conn.close()


def order_does_not_contain_dish(order_id: int, dish_id: int) -> ReturnValue:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                DELETE FROM OrderDishes WHERE order_id = {order_id} AND dish_id = {dish_id}
            """).format(
            order_id=sql.Literal(order_id),
            dish_id=sql.Literal(dish_id)
        )
        rows_affected, _ = conn.execute(query)
        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS
        return ReturnValue.OK
    except DatabaseException:
        return ReturnValue.ERROR
    finally:
        if conn:
            conn.close()


def get_all_order_items(order_id: int) -> List[OrderDish]:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT dish_id, amount, price_at_order
                FROM OrderDishes
                WHERE order_id = {order_id}
                ORDER BY dish_id ASC;
            """).format(order_id=sql.Literal(order_id))
        
        _ , result = conn.execute(query)

        order_dishes = []
        for idx in range(result.size()):
            row = result[idx]
            order_dish = OrderDish()
            order_dish.set_dish_id(row['dish_id'])
            order_dish.set_amount(row['amount'])
            order_dish.set_price(float(row['price_at_order']))
            order_dishes.append(order_dish)

        return order_dishes
    except DatabaseException:
        return []
    finally:
        if conn:
            conn.close()


def customer_rated_dish(cust_id: int, dish_id: int, rating: int) -> ReturnValue:
    if rating < 1 or rating > 5:
        return ReturnValue.BAD_PARAMS
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                INSERT INTO Ratings(customer_id, dish_id, rating)
                VALUES ({cust_id}, {dish_id}, {rating})
            """).format(
            cust_id=sql.Literal(cust_id),
            dish_id=sql.Literal(dish_id),
            rating=sql.Literal(rating)
        )
        conn.execute(query)
        return ReturnValue.OK
    except DatabaseException.FOREIGN_KEY_VIOLATION:
        return ReturnValue.NOT_EXISTS
    except DatabaseException.UNIQUE_VIOLATION:
        return ReturnValue.ALREADY_EXISTS
    except DatabaseException.CHECK_VIOLATION:
        return ReturnValue.BAD_PARAMS
    except DatabaseException:
        return ReturnValue.ERROR
    finally:
        if conn:
            conn.close()


def customer_deleted_rating_on_dish(cust_id: int, dish_id: int) -> ReturnValue:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                DELETE FROM Ratings
                WHERE customer_id = {cust_id} AND dish_id = {dish_id}
            """).format(
            cust_id=sql.Literal(cust_id),
            dish_id=sql.Literal(dish_id)
        )
        rows_affected, _ = conn.execute(query)
        if rows_affected == 0:
            return ReturnValue.NOT_EXISTS
        return ReturnValue.OK
    except DatabaseException:
        return ReturnValue.ERROR
    finally:
        if conn:
            conn.close()


def get_all_customer_ratings(cust_id: int) -> List[Tuple[int, int]]:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT dish_id, rating
                FROM Ratings
                WHERE customer_id = {cust_id}
                ORDER BY dish_id ASC;
            """).format(cust_id=sql.Literal(cust_id))
        
        _ , result = conn.execute(query)

        ratings = []
        for idx in range(result.size()):
            row = result[idx]
            ratings.append((row['dish_id'], row['rating']))

        return ratings
    except DatabaseException:
        return []
    finally:
        if conn:
            conn.close()

# ---------------------------------- BASIC API: ----------------------------------

# Basic API


def get_order_total_price(order_id: int) -> float:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT total_price
                FROM OrderTotals
                WHERE order_id = {order_id};
            """).format(order_id=sql.Literal(order_id))
        
        _ , result = conn.execute(query)
        if result.size() > 0:
            return float(result[0]['total_price'])
         
    except DatabaseException:
        pass
    finally:
        if conn:
            conn.close()
    return 0.0


def get_customers_spent_max_avg_amount_money() -> List[int]:
    conn = None
    customers = []
    try:
        conn = Connector.DBConnector()
        query = """
            WITH customer_avg AS (
                SELECT customer_id, AVG(total_price) AS avg_spent
                FROM OrderTotals
                WHERE customer_id IS NOT NULL
                GROUP BY customer_id
            )
            SELECT customer_id
            FROM customer_avg
            WHERE avg_spent = (SELECT MAX(avg_spent) FROM customer_avg)
            ORDER BY customer_id ASC;
        """
        
        _ , result = conn.execute(query)

        for idx in range(result.size()):
            customers.append(result[idx]['customer_id'])

    except DatabaseException:
        return []
    finally:
        if conn:
            conn.close()
    return customers


def get_most_profitable_dish_in_period(start: datetime, end: datetime) -> Dish:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                SELECT d.dish_id, d.name, d.price, d.is_active
                FROM OrderDishes od
                JOIN Orders o ON od.order_id = o.order_id
                JOIN Dishes d ON od.dish_id = d.dish_id
                WHERE o.date >= {start} AND o.date <= {end}
                GROUP BY d.dish_id, d.name, d.price, d.is_active
                ORDER BY SUM(od.amount * od.price_at_order) DESC , d.dish_id ASC
                LIMIT 1;
            """).format(
            start=sql.Literal(start),
            end=sql.Literal(end)
        )
        
        _ , result = conn.execute(query)
        if result.size() > 0:
            row = result[0]
            dish = Dish()
            dish.set_dish_id(row['dish_id'])
            dish.set_name(row['name'])
            dish.set_price(float(row['price']))
            dish.set_is_active(row['is_active'])
            return dish
    except DatabaseException:
        pass
    finally:
        if conn:
            conn.close()
    return BadDish()


def did_customer_order_top_rated_dishes(cust_id: int) -> bool:
    conn = None
    try:
        conn = Connector.DBConnector()
        query = sql.SQL("""
                WITH top_rated_dishes AS (
                    SELECT d.dish_id, COALESCE(AVG(r.rating), 3.0) AS avg_rating
                    FROM Dishes d
                    LEFT JOIN Ratings r ON d.dish_id = r.dish_id
                    GROUP BY d.dish_id
                    ORDER BY avg_rating DESC, d.dish_id ASC
                    LIMIT 5
                ),
                customer_orders AS (
                    SELECT DISTINCT od.dish_id
                    FROM OrderDishes od
                    JOIN Orders o ON od.order_id = o.order_id
                    WHERE o.customer_id = {cust_id}
                )
                SELECT EXISTS(
                    SELECT 1
                    FROM top_rated_dishes trd
                    JOIN customer_orders co ON trd.dish_id = co.dish_id
                ) AS did_order
            """).format(cust_id=sql.Literal(cust_id))
        
        _ , result = conn.execute(query)
        if result.size() > 0:
            did_order = bool(result[0]['did_order'])
            return did_order

    except DatabaseException:
        pass
    finally:
        if conn:
            conn.close()
    return False


# ---------------------------------- ADVANCED API: ----------------------------------

# Advanced API


def get_customers_rated_but_not_ordered() -> List[int]:
    conn = None
    customers = []
    try:
        conn = Connector.DBConnector()

        query = """
            WITH lowest_rated_dishes AS (
                SELECT d.dish_id
                FROM Dishes d
                LEFT JOIN Ratings r ON d.dish_id = r.dish_id
                GROUP BY d.dish_id
                ORDER BY COALESCE(AVG(r.rating), 3.0) ASC, d.dish_id ASC
                LIMIT 5
            )
            SELECT DISTINCT r.customer_id
            FROM Ratings r
            JOIN lowest_rated_dishes lrd ON r.dish_id = lrd.dish_id
            WHERE r.rating < 3
              AND NOT EXISTS (
                  SELECT 1
                  FROM Orders o
                  JOIN OrderDishes od ON o.order_id = od.order_id
                  WHERE o.customer_id = r.customer_id
                    AND od.dish_id = r.dish_id
              )
            ORDER BY r.customer_id ASC;
        """

        _, result = conn.execute(query)

        for idx in range(result.size()):
            customers.append(result[idx]['customer_id'])

    except DatabaseException:
        return []

    finally:
        if conn:
            conn.close()

    return customers


def get_non_worth_price_increase() -> List[int]:
    conn = None
    dishes = []
    try:
        conn = Connector.DBConnector()

        query = """
            WITH price_stats AS (
                SELECT 
                    dish_id,
                    price_at_order,
                    AVG(amount) * price_at_order AS avg_profit_per_order
                FROM OrderDishes
                GROUP BY dish_id, price_at_order
            ),
            current_price_stats AS (
                SELECT 
                    d.dish_id,
                    d.price AS current_price,
                    ps.avg_profit_per_order AS current_avg_profit
                FROM Dishes d
                JOIN price_stats ps 
                    ON d.dish_id = ps.dish_id 
                   AND d.price = ps.price_at_order
                WHERE d.is_active = TRUE
            )
            SELECT DISTINCT cps.dish_id
            FROM current_price_stats cps
            WHERE EXISTS (
                SELECT 1
                FROM price_stats old_ps
                WHERE old_ps.dish_id = cps.dish_id
                  AND old_ps.price_at_order < cps.current_price
                  AND old_ps.avg_profit_per_order > cps.current_avg_profit
            )
            ORDER BY cps.dish_id ASC;
        """

        _, result = conn.execute(query)

        for idx in range(result.size()):
            dishes.append(result[idx]['dish_id'])

    except DatabaseException:
        return []

    finally:
        if conn:
            conn.close()

    return dishes


def get_cumulative_profit_per_month(year: int) -> List[Tuple[int, float]]:
    conn = None
    profits = []
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
            WITH months(month) AS (
                SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
                UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
            ),
            order_prices AS (
                SELECT 
                    o.order_id,
                    EXTRACT(MONTH FROM o.date) AS month,
                    o.delivery_fee + o.tip + COALESCE(SUM(od.amount * od.price_at_order), 0) AS order_profit
                FROM Orders o
                LEFT JOIN OrderDishes od ON o.order_id = od.order_id
                WHERE EXTRACT(YEAR FROM o.date) = {year}
                GROUP BY o.order_id, o.date, o.delivery_fee, o.tip
            ),
            monthly_profit AS (
                SELECT 
                    month,
                    SUM(order_profit) AS profit
                FROM order_prices
                GROUP BY month
            )
            SELECT 
                m.month,
                COALESCE(SUM(mp.profit), 0) AS cumulative_profit
            FROM months m
            LEFT JOIN monthly_profit mp ON mp.month <= m.month
            GROUP BY m.month
            ORDER BY m.month DESC;
        """).format(
            year=sql.Literal(year)
        )

        _, result = conn.execute(query)

        for idx in range(result.size()):
            row = result[idx]
            profits.append((row['month'], float(row['cumulative_profit'])))

    except DatabaseException:
        return []

    finally:
        if conn:
            conn.close()

    return profits


def get_potential_dish_recommendations(cust_id: int) -> List[int]:
    conn = None
    recommendations = []
    try:
        conn = Connector.DBConnector()

        query = sql.SQL("""
            WITH RECURSIVE similar_customers(customer_id) AS (
                SELECT DISTINCT r2.customer_id
                FROM Ratings r1
                JOIN Ratings r2 ON r1.dish_id = r2.dish_id
                WHERE r1.customer_id = {cust_id}
                  AND r1.rating >= 4
                  AND r2.rating >= 4
                  AND r2.customer_id <> {cust_id}

                UNION

                SELECT DISTINCT r2.customer_id
                FROM similar_customers sc
                JOIN Ratings r1 
                    ON sc.customer_id = r1.customer_id
                JOIN Ratings r2 
                    ON r1.dish_id = r2.dish_id
                WHERE r1.rating >= 4
                  AND r2.rating >= 4
                  AND r2.customer_id <> {cust_id}
            )
            SELECT DISTINCT r.dish_id
            FROM Ratings r
            JOIN similar_customers sc 
                ON r.customer_id = sc.customer_id
            WHERE r.rating >= 4
              AND NOT EXISTS (
                  SELECT 1
                  FROM Orders o
                  JOIN OrderDishes od 
                      ON o.order_id = od.order_id
                  WHERE o.customer_id = {cust_id}
                    AND od.dish_id = r.dish_id
              )
            ORDER BY r.dish_id ASC;
        """).format(
            cust_id=sql.Literal(cust_id)
        )

        _, result = conn.execute(query)

        for idx in range(result.size()):
            recommendations.append(result[idx]['dish_id'])

    except DatabaseException:
        return []

    finally:
        if conn:
            conn.close()

    return recommendations
