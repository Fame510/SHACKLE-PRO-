// SHACKLE Rust Core — Hot Path
// ================================
// If Python decide() > 0.1ms, rewrite here with pyo3 bindings.
//
// This file is a placeholder showing the intended API surface.
// Full implementation when performance demands it.

use pyo3::prelude::*;
use sha2::{Sha256, Digest};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum Verdict {
    Allow,
    Deny,
    Hitl,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DenyReason {
    Unspecified,
    BudgetExhausted,
    MaxRepeatExceeded,
    CircuitOpen,
    WindowExceeded,
    GlobalLimit,
    PolicyViolation,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GuardConfig {
    pub budget_usd: f64,
    pub max_repeat_calls: u32,
    pub error_amplification: bool,
    pub max_total_calls: u64,
    pub probabilistic_deny: bool,
    pub deny_jitter_ratio: f64,
    pub hitl_mode: String,
    pub hitl_budget_threshold: f64,
}

#[derive(Debug, Clone)]
pub struct SessionState {
    pub circuit_tripped: bool,
    pub circuit_trip_reason: String,
    pub budget_initial_usd: f64,
    pub budget_remaining_usd: f64,
    pub budget_spent_usd: f64,
    pub total_calls: u64,
    pub repeat_counts: HashMap<String, u32>,
    pub window_counts: HashMap<String, u32>,
    pub last_tool_name: String,
    pub last_tool_params_hash: Vec<u8>,
    pub seen_nonces: HashSet<u64>,
}

#[derive(Debug, Clone)]
pub struct ToolCall {
    pub tool_name: String,
    pub tool_params_hash: Vec<u8>,
    pub estimated_cost_usd: f64,
    pub nonce: u64,
    pub tool_params_raw: String,
}

#[derive(Debug, Clone)]
pub struct Decision {
    pub verdict: Verdict,
    pub deny_reason: DenyReason,
    pub human_readable: String,
    pub probabilistic_deny: bool,
}

const ERROR_SIGNALS: &[&str] = &[
    "401", "unauthorized", "403", "forbidden", "500",
    "internal server error", "502", "bad gateway", "503",
    "timeout", "connection refused", "rate limit",
    "permission denied", "access denied",
];

fn has_error_signal(params_raw: &str) -> bool {
    let lower = params_raw.to_lowercase();
    ERROR_SIGNALS.iter().any(|s| lower.contains(s))
}

/// The core decision function — Rust implementation.
/// Target: <0.01ms (10μs) — 10x faster than Python.
pub fn decide(
    state: &SessionState,
    call: &ToolCall,
    config: &GuardConfig,
    rng_float: f64,
) -> Decision {
    // Layer 1: Circuit breaker
    if state.circuit_tripped {
        return Decision {
            verdict: Verdict::Deny,
            deny_reason: DenyReason::CircuitOpen,
            human_readable: format!("Circuit open: {}", state.circuit_trip_reason),
            probabilistic_deny: false,
        };
    }

    // Layer 2: Nonce
    if state.seen_nonces.contains(&call.nonce) {
        return Decision {
            verdict: Verdict::Deny,
            deny_reason: DenyReason::PolicyViolation,
            human_readable: "Duplicate nonce".into(),
            probabilistic_deny: false,
        };
    }

    // Layer 3: Budget
    if config.budget_usd > 0.0 {
        if state.budget_remaining_usd <= 0.0 {
            return Decision {
                verdict: Verdict::Deny,
                deny_reason: DenyReason::BudgetExhausted,
                human_readable: format!("Budget exhausted: ${:.4}", state.budget_spent_usd),
                probabilistic_deny: false,
            };
        }
        if call.estimated_cost_usd > state.budget_remaining_usd {
            return Decision {
                verdict: Verdict::Deny,
                deny_reason: DenyReason::BudgetExhausted,
                human_readable: format!("Cost ${:.4} > remaining ${:.4}",
                    call.estimated_cost_usd, state.budget_remaining_usd),
                probabilistic_deny: false,
            };
        }
    }

    // Layer 4: Repeat calls
    if config.max_repeat_calls > 0 {
        let is_repeat = call.tool_name == state.last_tool_name
            && call.tool_params_hash == state.last_tool_params_hash;
        if is_repeat {
            let count = state.repeat_counts.get(&call.tool_name).copied().unwrap_or(0);
            let mut limit = config.max_repeat_calls;
            if config.error_amplification && has_error_signal(&call.tool_params_raw) {
                limit = std::cmp::max(1, config.max_repeat_calls - 1);
            }
            if count >= limit {
                return Decision {
                    verdict: Verdict::Deny,
                    deny_reason: DenyReason::MaxRepeatExceeded,
                    human_readable: format!("{} repeated {}x", call.tool_name, count + 1),
                    probabilistic_deny: false,
                };
            }
        }
    }

    // Layer 5: Global limit
    if config.max_total_calls > 0 && state.total_calls >= config.max_total_calls {
        return Decision {
            verdict: Verdict::Deny,
            deny_reason: DenyReason::GlobalLimit,
            human_readable: format!("Global limit: {}", state.total_calls),
            probabilistic_deny: false,
        };
    }

    // Layer 6: Probabilistic deny
    if config.probabilistic_deny && config.budget_usd > 0.0 && state.budget_initial_usd > 0.0 {
        let ratio = state.budget_remaining_usd / state.budget_initial_usd;
        if ratio < 0.2 {
            let prob = config.deny_jitter_ratio * (1.0 - ratio);
            if rng_float < prob {
                return Decision {
                    verdict: Verdict::Deny,
                    deny_reason: DenyReason::BudgetExhausted,
                    human_readable: "Budget enforcement (probabilistic)".into(),
                    probabilistic_deny: true,
                };
            }
        }
    }

    Decision {
        verdict: Verdict::Allow,
        deny_reason: DenyReason::Unspecified,
        human_readable: "Within all guard thresholds".into(),
        probabilistic_deny: false,
    }
}

/// Python binding via pyo3 — drop-in replacement for Python decide()
#[pyfunction]
fn decide_py(
    state_json: &str,
    call_json: &str,
    config_json: &str,
    rng_float: f64,
) -> PyResult<String> {
    // Deserialize, call decide(), serialize result
    // (Full implementation when Python is too slow)
    Ok("{\"verdict\": \"ALLOW\"}".into())
}

#[pymodule]
fn shackle_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(decide_py, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_circuit_breaker() {
        let state = SessionState {
            circuit_tripped: true,
            circuit_trip_reason: "test".into(),
            budget_initial_usd: 1.0,
            budget_remaining_usd: 1.0,
            budget_spent_usd: 0.0,
            total_calls: 0,
            repeat_counts: HashMap::new(),
            window_counts: HashMap::new(),
            last_tool_name: "".into(),
            last_tool_params_hash: vec![],
            seen_nonces: HashSet::new(),
        };
        let call = ToolCall {
            tool_name: "test".into(),
            tool_params_hash: vec![1, 2, 3],
            estimated_cost_usd: 0.01,
            nonce: 1,
            tool_params_raw: "{}".into(),
        };
        let config = GuardConfig {
            budget_usd: 1.0,
            max_repeat_calls: 3,
            error_amplification: true,
            max_total_calls: 100,
            probabilistic_deny: false,
            deny_jitter_ratio: 0.0,
            hitl_mode: "never".into(),
            hitl_budget_threshold: 0.0,
        };
        let d = decide(&state, &call, &config, 0.5);
        assert!(matches!(d.verdict, Verdict::Deny));
    }
}
