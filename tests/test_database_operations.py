"""
Test that measures SQLite database performance in the sandbox environment.

This test evaluates database operations including connections, schema creation,
data insertion, querying, transactions, and concurrent access.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_database_operations():
    """
    Measures SQLite database operations performance.
    
    This test evaluates:
    - Database connection speed
    - Schema creation performance
    - Data insertion rates for multiple tables
    - Query performance (simple, join, and complex queries)
    - Transaction handling with commits and rollbacks
    - Concurrent query execution
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=True,  # Only need to run once per benchmark session
    )
    
    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer=True,  # Need timing for benchmark
        include_results=True,  # Need results formatting
        include_packages=False  # Using only standard library SQLite
    )
    
    # Define the test-specific code
    test_code = """
import sqlite3
import time
import os
import random
import string
import tempfile
from concurrent.futures import ThreadPoolExecutor

class DatabaseBenchmark:
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        
    def connect(self):
        # Establish database connection
        start_time = time.time()
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        elapsed = time.time() - start_time
        return elapsed
    
    def create_tables(self):
        # Create test tables
        start_time = time.time()
        
        # Users table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Posts table with foreign key to users
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Comments table with foreign keys to users and posts
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
        ''')
        
        # Create indexes
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts (user_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments (post_id)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_user_id ON comments (user_id)')
        
        self.connection.commit()
        elapsed = time.time() - start_time
        return elapsed
    
    def generate_random_string(self, length=10):
        # Generate a random string of specified length
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def insert_users(self, count):
        # Insert a specified number of users
        start_time = time.time()
        
        for i in range(count):
            username = f"user_{self.generate_random_string(8)}"
            email = f"{username}@example.com"
            password_hash = self.generate_random_string(32)
            
            self.cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
        
        self.connection.commit()
        elapsed = time.time() - start_time
        return elapsed
    
    def insert_posts(self, count, user_count):
        # Insert a specified number of posts
        start_time = time.time()
        
        for i in range(count):
            user_id = random.randint(1, user_count)
            title = f"Post {i} - {self.generate_random_string(20)}"
            content = self.generate_random_string(200)
            
            self.cursor.execute(
                "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
                (user_id, title, content)
            )
        
        self.connection.commit()
        elapsed = time.time() - start_time
        return elapsed
    
    def insert_comments(self, count, user_count, post_count):
        # Insert a specified number of comments
        start_time = time.time()
        
        for i in range(count):
            user_id = random.randint(1, user_count)
            post_id = random.randint(1, post_count)
            content = self.generate_random_string(100)
            
            self.cursor.execute(
                "INSERT INTO comments (user_id, post_id, content) VALUES (?, ?, ?)",
                (user_id, post_id, content)
            )
        
        self.connection.commit()
        elapsed = time.time() - start_time
        return elapsed
    
    def run_simple_query(self):
        # Run a simple query that fetches users
        start_time = time.time()
        
        self.cursor.execute("SELECT * FROM users LIMIT 100")
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_join_query(self):
        # Run a query with JOIN operations
        start_time = time.time()
        
        self.cursor.execute('''
        SELECT u.username, p.title, COUNT(c.id) as comment_count
        FROM users u
        JOIN posts p ON u.id = p.user_id
        LEFT JOIN comments c ON p.id = c.post_id
        GROUP BY p.id
        ORDER BY comment_count DESC
        LIMIT 50
        ''')
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_complex_query(self):
        # Run a more complex query with subqueries and aggregations
        start_time = time.time()
        
        self.cursor.execute('''
        SELECT 
            u.username,
            (SELECT COUNT(*) FROM posts WHERE user_id = u.id) as post_count,
            (SELECT COUNT(*) FROM comments WHERE user_id = u.id) as comment_count,
            (SELECT AVG(LENGTH(content)) FROM posts WHERE user_id = u.id) as avg_post_length
        FROM users u
        WHERE (SELECT COUNT(*) FROM posts WHERE user_id = u.id) > 0
        ORDER BY post_count DESC, comment_count DESC
        LIMIT 25
        ''')
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_transaction_test(self, iterations):
        # Test transaction performance with rollbacks
        start_time = time.time()
        successful = 0
        
        for i in range(iterations):
            try:
                self.connection.execute("BEGIN TRANSACTION")
                
                # Insert a new user
                username = f"transaction_user_{i}_{self.generate_random_string(8)}"
                email = f"{username}@example.com"
                password_hash = self.generate_random_string(32)
                
                self.cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                
                # Get the new user's ID
                self.cursor.execute("SELECT last_insert_rowid()")
                user_id = self.cursor.fetchone()[0]
                
                # Insert a post for this user
                title = f"Transaction post {i}"
                content = self.generate_random_string(100)
                
                self.cursor.execute(
                    "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
                    (user_id, title, content)
                )
                
                # Randomly decide to commit or rollback
                if random.random() < 0.8:  # 80% chance to commit
                    self.connection.commit()
                    successful += 1
                else:
                    self.connection.rollback()
                
            except Exception as e:
                self.connection.rollback()
                print(f"Transaction failed: {e}")
        
        elapsed = time.time() - start_time
        return elapsed, successful
    
    def run_concurrent_queries(self, num_workers):
        # Test concurrent query execution
        query_types = [
            ("simple", lambda: self.run_simple_query()[0]),
            ("join", lambda: self.run_join_query()[0]),
            ("complex", lambda: self.run_complex_query()[0])
        ]
        
        results = {
            "simple": [],
            "join": [],
            "complex": []
        }
        
        def execute_query(query_tuple):
            query_type, query_func = query_tuple
            elapsed = query_func()
            return query_type, elapsed
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit 30 random queries
            futures = []
            for _ in range(30):
                query_tuple = random.choice(query_types)
                futures.append(executor.submit(execute_query, query_tuple))
            
            for future in futures:
                try:
                    query_type, elapsed = future.result()
                    results[query_type].append(elapsed)
                except Exception as e:
                    print(f"Concurrent query failed: {e}")
        
        total_elapsed = time.time() - start_time
        
        # Calculate average times
        avg_results = {}
        for query_type, times in results.items():
            if times:
                avg_results[query_type] = sum(times) / len(times)
            else:
                avg_results[query_type] = None
        
        return total_elapsed, avg_results
    
    def close(self):
        # Close database connection
        if self.connection:
            self.connection.close()

def run_database_benchmark():
    # Create a temporary database file
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
        db_path = temp_db.name
    
    print("\\n=== SQLite Database Performance Benchmark ===")
    
    # Initialize benchmark
    benchmark = DatabaseBenchmark(db_path)
    
    # Connect to database
    connect_time = benchmark.connect()
    print(f"Database connection established in {connect_time:.4f}s")
    
    # Create schema
    schema_time = benchmark.create_tables()
    print(f"Schema created in {schema_time:.4f}s")
    
    # Try to detect system resources to scale the test appropriately
    try:
        # Use resource detection if available (added in our improved utils)
        resources = detect_resource_constraints()
        
        # Scale data size based on available memory 
        resource_scale = resources.get('resource_scale', 0.5)
        print(f"Scaling database test to {resource_scale * 100:.0f}% based on system resources")
        
        # Scale data generation parameters based on available resources
        user_count = int(1000 * resource_scale)
        post_count = int(5000 * resource_scale)
        comment_count = int(20000 * resource_scale)
    except Exception as e:
        # Fallback to conservative defaults if detection fails
        print(f"Resource detection failed: {e}, using conservative defaults")
        user_count = 500
        post_count = 2500  
        comment_count = 10000
    
    # Insert test data
    print("\\n1. Data Insertion Performance")
    user_insert_time = benchmark.insert_users(user_count)
    print(f"  - Inserted {user_count} users in {user_insert_time:.4f}s ({user_count/user_insert_time:.2f} records/s)")
    
    post_insert_time = benchmark.insert_posts(post_count, user_count)
    print(f"  - Inserted {post_count} posts in {post_insert_time:.4f}s ({post_count/post_insert_time:.2f} records/s)")
    
    comment_insert_time = benchmark.insert_comments(comment_count, user_count, post_count)
    print(f"  - Inserted {comment_count} comments in {comment_insert_time:.4f}s ({comment_count/comment_insert_time:.2f} records/s)")
    
    # Query performance tests
    print("\\n2. Query Performance")
    try:
        simple_query_time, simple_query_results = benchmark.run_simple_query()
        print(f"  - Simple query: {simple_query_time:.4f}s, {simple_query_results} results")
    except Exception as e:
        print(f"  - Simple query failed: {e}")
        simple_query_time, simple_query_results = 0, 0
    
    try:
        join_query_time, join_query_results = benchmark.run_join_query()
        print(f"  - Join query: {join_query_time:.4f}s, {join_query_results} results")
    except Exception as e:
        print(f"  - Join query failed: {e}")
        join_query_time, join_query_results = 0, 0
    
    try:
        complex_query_time, complex_query_results = benchmark.run_complex_query()
        print(f"  - Complex query: {complex_query_time:.4f}s, {complex_query_results} results")
    except Exception as e:
        print(f"  - Complex query failed: {e}")
        complex_query_time, complex_query_results = 0, 0
    
    # Transaction tests - scale iterations based on previous performance
    print("\\n3. Transaction Performance")
    # Scale transaction iterations based on how fast the queries were
    # to avoid timeouts on slow environments
    if simple_query_time > 1.0 or join_query_time > 1.0:
        # Reduce transaction count for slow environments
        transaction_iterations = 50
    else:
        transaction_iterations = 100
        
    try:
        transaction_time, successful_transactions = benchmark.run_transaction_test(transaction_iterations)
        print(f"  - {transaction_iterations} transactions ({successful_transactions} committed, {transaction_iterations - successful_transactions} rolled back)")
        print(f"  - Total time: {transaction_time:.4f}s ({transaction_iterations/transaction_time:.2f} transactions/s)")
    except Exception as e:
        print(f"  - Transaction test failed: {e}")
        transaction_time, successful_transactions = 0, 0
    
    # Concurrent query tests - scale workers based on earlier performance
    print("\\n4. Concurrent Query Performance")
    # Adjust worker count based on system capabilities and previous performance
    if 'resources' in locals() and 'cpu_count' in resources:
        # Scale workers based on CPU count but not more than 5
        concurrent_workers = min(5, max(2, resources.get('cpu_count', 2) - 1))
    else:
        # Conservative default
        concurrent_workers = 3
        
    # If previous tests were slow, further reduce concurrency to avoid timeouts
    if transaction_time > 5.0 or complex_query_time > 2.0:
        concurrent_workers = 2
        
    print(f"  - Using {concurrent_workers} concurrent workers based on system capabilities")
    
    try:
        concurrent_time, concurrent_avg = benchmark.run_concurrent_queries(concurrent_workers)
        print(f"  - Total time: {concurrent_time:.4f}s")
        
        # Safely print average times, handling None values
        simple_avg = concurrent_avg.get('simple', None)
        join_avg = concurrent_avg.get('join', None)
        complex_avg = concurrent_avg.get('complex', None)
        
        print(f"  - Average query times: Simple: {simple_avg:.4f}s if simple_avg else 'N/A'}, " + 
              f"Join: {join_avg:.4f}s if join_avg else 'N/A'}, " + 
              f"Complex: {complex_avg:.4f}s if complex_avg else 'N/A'}")
    except Exception as e:
        print(f"  - Concurrent query test failed: {e}")
        concurrent_time = 1.0  # Default value to avoid division by zero
        concurrent_avg = {'simple': None, 'join': None, 'complex': None}
    
    # Close connection and clean up
    benchmark.close()
    
    # Summary
    print("\\n=== Database Performance Summary ===")
    print(f"Connection time: {connect_time:.4f}s")
    print(f"Schema creation time: {schema_time:.4f}s")
    print(f"Data insertion rate: {(user_count + post_count + comment_count) / (user_insert_time + post_insert_time + comment_insert_time):.2f} records/s")
    print(f"Simple query time: {simple_query_time:.4f}s")
    print(f"Join query time: {join_query_time:.4f}s")
    print(f"Complex query time: {complex_query_time:.4f}s")
    print(f"Transaction throughput: {transaction_iterations/transaction_time:.2f} transactions/s")
    print(f"Concurrent query throughput: {30/concurrent_time:.2f} queries/s")
    
    # Clean up temporary file
    try:
        os.unlink(db_path)
    except:
        pass
    
    return {
        "connection_time": connect_time,
        "schema_time": schema_time,
        "data_insertion": {
            "users": user_insert_time,
            "posts": post_insert_time,
            "comments": comment_insert_time,
            "total_rate": (user_count + post_count + comment_count) / (user_insert_time + post_insert_time + comment_insert_time)
        },
        "query_performance": {
            "simple": simple_query_time,
            "join": join_query_time,
            "complex": complex_query_time
        },
        "transaction_throughput": transaction_iterations/transaction_time,
        "concurrent_throughput": 30/concurrent_time
    }

@benchmark_timer
def timed_test():
    return run_database_benchmark()

# Run the benchmark
test_result = timed_test()

# Print the results using the utility function
print_benchmark_results(test_result)
"""

    # Combine the utilities and test code
    full_code = f"{utils_code}\n\n{test_code}"

    # Return the test configuration and code
    return {
        "config": config,
        "code": full_code
    }