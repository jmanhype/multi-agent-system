#!/usr/bin/env python
"""
Database Manager for Grid Search and Portfolio Results
Stores all backtest results, parameters, and analytics
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage storage of grid search results and portfolio analytics"""
    
    def __init__(self, db_path: str = "db/grid_results.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Grid search results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS grid_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                asset TEXT NOT NULL,
                strategy_type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                sharpe_ratio REAL,
                total_return REAL,
                win_rate REAL,
                max_drawdown REAL,
                num_trades INTEGER,
                profit_factor REAL,
                avg_trade_return REAL,
                best_trade REAL,
                worst_trade REAL,
                metadata TEXT
            )
        ''')
        
        # Portfolio analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                portfolio_config TEXT NOT NULL,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                correlation_matrix TEXT,
                asset_weights TEXT,
                best_asset TEXT,
                worst_asset TEXT,
                metadata TEXT
            )
        ''')
        
        # Trade analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                asset TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                trade_type TEXT,
                entry_time DATETIME,
                exit_time DATETIME,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                hold_time_hours REAL,
                market_condition TEXT,
                exit_reason TEXT
            )
        ''')
        
        # Strategy evolution table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                generation INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                strategy_config TEXT NOT NULL,
                fitness_score REAL,
                parent_strategy TEXT,
                mutation_type TEXT,
                performance_metrics TEXT
            )
        ''')
        
        self.conn.commit()
    
    def save_grid_result(self, session_id: str, asset: str, strategy_type: str,
                        parameters: Dict, metrics: Dict, metadata: Dict = None):
        """Save a single grid search result"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO grid_results (
                session_id, asset, strategy_type, parameters,
                sharpe_ratio, total_return, win_rate, max_drawdown,
                num_trades, profit_factor, avg_trade_return,
                best_trade, worst_trade, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            asset,
            strategy_type,
            json.dumps(parameters),
            metrics.get('sharpe_ratio', 0),
            metrics.get('total_return', 0),
            metrics.get('win_rate', 0),
            metrics.get('max_drawdown', 0),
            metrics.get('num_trades', 0),
            metrics.get('profit_factor', 0),
            metrics.get('avg_trade_return', 0),
            metrics.get('best_trade', 0),
            metrics.get('worst_trade', 0),
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def save_portfolio_result(self, session_id: str, portfolio_config: Dict,
                            metrics: Dict, metadata: Dict = None):
        """Save portfolio-level results"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO portfolio_results (
                session_id, portfolio_config, total_return, sharpe_ratio,
                max_drawdown, correlation_matrix, asset_weights,
                best_asset, worst_asset, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            json.dumps(portfolio_config),
            metrics.get('total_return', 0),
            metrics.get('sharpe_ratio', 0),
            metrics.get('max_drawdown', 0),
            json.dumps(metrics.get('correlation_matrix', {})),
            json.dumps(metrics.get('asset_weights', {})),
            metrics.get('best_asset', ''),
            metrics.get('worst_asset', ''),
            json.dumps(metadata) if metadata else None
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def save_trade(self, session_id: str, asset: str, trade: Dict):
        """Save individual trade data"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO trade_analytics (
                session_id, asset, trade_type, entry_time, exit_time,
                entry_price, exit_price, pnl, pnl_pct,
                hold_time_hours, market_condition, exit_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            asset,
            trade.get('trade_type', 'long'),
            trade.get('entry_time'),
            trade.get('exit_time'),
            trade.get('entry_price', 0),
            trade.get('exit_price', 0),
            trade.get('pnl', 0),
            trade.get('pnl_pct', 0),
            trade.get('hold_time_hours', 0),
            trade.get('market_condition', ''),
            trade.get('exit_reason', '')
        ))
        
        self.conn.commit()
    
    def save_evolution_step(self, session_id: str, generation: int,
                           strategy_config: Dict, fitness: float,
                           parent: str = None, mutation: str = None,
                           metrics: Dict = None):
        """Save strategy evolution step"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO strategy_evolution (
                session_id, generation, strategy_config, fitness_score,
                parent_strategy, mutation_type, performance_metrics
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            generation,
            json.dumps(strategy_config),
            fitness,
            parent,
            mutation,
            json.dumps(metrics) if metrics else None
        ))
        
        self.conn.commit()
    
    def get_best_strategies(self, limit: int = 10, min_sharpe: float = 0) -> pd.DataFrame:
        """Get best performing strategies from database"""
        query = '''
            SELECT * FROM grid_results
            WHERE sharpe_ratio > ?
            ORDER BY sharpe_ratio DESC
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, self.conn, params=(min_sharpe, limit))
        
        # Parse JSON fields
        if not df.empty:
            df['parameters'] = df['parameters'].apply(json.loads)
            df['metadata'] = df['metadata'].apply(lambda x: json.loads(x) if x else {})
        
        return df
    
    def get_session_results(self, session_id: str) -> Dict:
        """Get all results for a specific session"""
        results = {}
        
        # Get grid results
        grid_query = 'SELECT * FROM grid_results WHERE session_id = ?'
        results['grid_results'] = pd.read_sql_query(grid_query, self.conn, params=(session_id,))
        
        # Get portfolio results
        portfolio_query = 'SELECT * FROM portfolio_results WHERE session_id = ?'
        results['portfolio_results'] = pd.read_sql_query(portfolio_query, self.conn, params=(session_id,))
        
        # Get trade analytics
        trade_query = 'SELECT * FROM trade_analytics WHERE session_id = ?'
        results['trades'] = pd.read_sql_query(trade_query, self.conn, params=(session_id,))
        
        # Get evolution history
        evolution_query = 'SELECT * FROM strategy_evolution WHERE session_id = ? ORDER BY generation'
        results['evolution'] = pd.read_sql_query(evolution_query, self.conn, params=(session_id,))
        
        return results
    
    def get_asset_comparison(self, session_id: str = None) -> pd.DataFrame:
        """Get performance comparison across assets"""
        if session_id:
            query = '''
                SELECT asset, 
                       AVG(sharpe_ratio) as avg_sharpe,
                       AVG(total_return) as avg_return,
                       AVG(win_rate) as avg_win_rate,
                       AVG(max_drawdown) as avg_drawdown,
                       COUNT(*) as strategy_count
                FROM grid_results
                WHERE session_id = ?
                GROUP BY asset
                ORDER BY avg_sharpe DESC
            '''
            return pd.read_sql_query(query, self.conn, params=(session_id,))
        else:
            query = '''
                SELECT asset, 
                       AVG(sharpe_ratio) as avg_sharpe,
                       AVG(total_return) as avg_return,
                       AVG(win_rate) as avg_win_rate,
                       AVG(max_drawdown) as avg_drawdown,
                       COUNT(*) as strategy_count
                FROM grid_results
                GROUP BY asset
                ORDER BY avg_sharpe DESC
            '''
            return pd.read_sql_query(query, self.conn)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Singleton instance
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get or create the singleton DatabaseManager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager