def test_database_operations():
    # This test should only run once per provider
    test_database_operations.single_run = True
    return """import sqlite3
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
        """Establish database connection"""
        start_time = time.time()
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        elapsed = time.time() - start_time
        return elapsed
    
    def create_tables(self):
        """Create test tables"""
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
        """Generate a random string of specified length"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def insert_users(self, count):
        """Insert a specified number of users"""
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
        """Insert a specified number of posts"""
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
        """Insert a specified number of comments"""
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
        """Run a simple query that fetches users"""
        start_time = time.time()
        
        self.cursor.execute("SELECT * FROM users LIMIT 100")
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_join_query(self):
        """Run a query with JOIN operations"""
        start_time = time.time()
        
        self.cursor.execute("""
        SELECT u.username, p.title, COUNT(c.id) as comment_count
        FROM users u
        JOIN posts p ON u.id = p.user_id
        LEFT JOIN comments c ON p.id = c.post_id
        GROUP BY p.id
        ORDER BY comment_count DESC
        LIMIT 50
        """)
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_complex_query(self):
        """Run a more complex query with subqueries and aggregations"""
        start_time = time.time()
        
        self.cursor.execute("""
        SELECT 
            u.username,
            (SELECT COUNT(*) FROM posts WHERE user_id = u.id) as post_count,
            (SELECT COUNT(*) FROM comments WHERE user_id = u.id) as comment_count,
            (SELECT AVG(LENGTH(content)) FROM posts WHERE user_id = u.id) as avg_post_length
        FROM users u
        WHERE (SELECT COUNT(*) FROM posts WHERE user_id = u.id) > 0
        ORDER BY post_count DESC, comment_count DESC
        LIMIT 25
        """)
        results = self.cursor.fetchall()
        
        elapsed = time.time() - start_time
        return elapsed, len(results)
    
    def run_transaction_test(self, iterations):
        """Test transaction performance with rollbacks"""
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
        """Test concurrent query execution"""
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
        """Close database connection"""
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
    
    # Data generation parameters
    user_count = 1000
    post_count = 5000
    comment_count = 20000
    
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
    simple_query_time, simple_query_results = benchmark.run_simple_query()
    print(f"  - Simple query: {simple_query_time:.4f}s, {simple_query_results} results")
    
    join_query_time, join_query_results = benchmark.run_join_query()
    print(f"  - Join query: {join_query_time:.4f}s, {join_query_results} results")
    
    complex_query_time, complex_query_results = benchmark.run_complex_query()
    print(f"  - Complex query: {complex_query_time:.4f}s, {complex_query_results} results")
    
    # Transaction tests
    print("\\n3. Transaction Performance")
    transaction_iterations = 100
    transaction_time, successful_transactions = benchmark.run_transaction_test(transaction_iterations)
    print(f"  - {transaction_iterations} transactions ({successful_transactions} committed, {transaction_iterations - successful_transactions} rolled back)")
    print(f"  - Total time: {transaction_time:.4f}s ({transaction_iterations/transaction_time:.2f} transactions/s)")
    
    # Concurrent query tests
    print("\\n4. Concurrent Query Performance")
    concurrent_workers = 5
    concurrent_time, concurrent_avg = benchmark.run_concurrent_queries(concurrent_workers)
    print(f"  - {concurrent_workers} concurrent workers, total time: {concurrent_time:.4f}s")
    print(f"  - Average query times: Simple: {concurrent_avg['simple']:.4f}s, Join: {concurrent_avg['join']:.4f}s, Complex: {concurrent_avg['complex']:.4f}s")
    
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

# Run the database benchmark
run_database_benchmark()
"""