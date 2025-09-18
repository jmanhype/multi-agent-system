# Crypto Trader (*/5 * * * *)
Agent: trader-orchestrator
Commands: ccxt-exchange, journal.append, metrics.write
Hooks: guard_approve (live), circuit_breaker (breach)