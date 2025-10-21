## Product Requirements Document: Forex Algo Trading Software (MQL4)

**Product Name:** AutoTrade FX (Placeholder Name - to be finalized)
**Version:** 1.0
**Date:** October 26, 2023
**Author:** AI Product Manager

---

### 1. Executive Summary

The AutoTrade FX project aims to develop a fully automated algorithmic trading software leveraging the MQL4 platform. This software will empower retail and professional forex traders to execute trading strategies automatically, eliminate emotional decision-making, and potentially enhance trading efficiency and profitability. The core objective is to provide a reliable, robust, and user-friendly solution for automated forex trading, reducing the manual effort and time commitment traditionally associated with active trading.

---

### 2. Project Overview

**2.1 Project Description**
AutoTrade FX is a high-performance algorithmic trading software designed to operate within the MetaTrader 4 (MT4) platform. It will automate the entire trading process, from market analysis and signal generation to order execution and risk management, based on predefined MQL4 code. The software will be built with a focus on reliability, backtesting capabilities, and extensibility to accommodate various trading strategies.

**2.2 Goals**
*   **Automate Trading Operations:** Enable users to fully automate their forex trading strategies, freeing up time and reducing manual intervention.
*   **Reduce Emotional Trading:** Eliminate psychological biases and emotional decision-making from trading activities.
*   **Enhance Trading Efficiency:** Facilitate faster trade execution and consistent strategy application.
*   **Improve Risk Management:** Incorporate robust risk management features to protect capital.
*   **Provide Backtesting Capabilities:** Allow users to thoroughly test and optimize their strategies using historical data.
*   **Deliver a User-Friendly Experience:** Ensure easy installation, configuration, and monitoring within the MT4 environment.

**2.3 Target Users**
*   **Retail Forex Traders:** Individuals seeking to automate their existing trading strategies or explore algorithmic trading without extensive programming knowledge.
*   **Professional Forex Traders/Money Managers:** Traders looking to scale their operations, implement complex strategies, or manage multiple accounts more efficiently.
*   **Aspiring Algo Traders/Developers:** Individuals interested in utilizing MQL4 for their own algorithmic trading development, potentially using this as a robust foundation.

**2.4 Problems Solved**
*   **Time Commitment:** Manual trading requires significant time for market analysis, monitoring, and execution. AutoTrade FX automates these tasks.
*   **Emotional Trading:** Fear, greed, and other emotions often lead to suboptimal trading decisions. Automation removes this human element.
*   **Inconsistent Strategy Execution:** Manual execution can be inconsistent, leading to deviations from a predefined strategy. Automation ensures consistent application.
*   **Missed Opportunities:** Traders can miss profitable setups if they are not actively monitoring the markets. AutoTrade FX operates 24/5.
*   **Complexity of Advanced Strategies:** Implementing complex, multi-indicator strategies manually can be challenging. Algo trading can handle this systematically.

---

### 3. Functional Requirements

**3.1 Core Trading Engine**
*   **FR-ETE-001: Market Data Integration:** The software shall seamlessly receive real-time market data (quotes, tick data) from the MT4 platform.
*   **FR-ETE-002: Strategy Execution:** The software shall execute predefined trading strategies based on MQL4 code, including entry, exit, Stop Loss (SL), and Take Profit (TP) orders.
*   **FR-ETE-003: Order Management:** The software shall be capable of placing, modifying, and canceling various order types (Market Order, Limit Order, Stop Order).
*   **FR-ETE-004: Position Management:** The software shall track and manage open positions, including calculating profit/loss, margin usage, and equity.
*   **FR-ETE-005: Trade Execution Logging:** The software shall maintain a detailed log of all trading activities, including order placement, modification, and execution timestamps.

**3.2 Risk Management Module**
*   **FR-RMM-001: Position Sizing:** The software shall allow users to define position sizing rules (e.g., fixed lot size, percentage of equity, risk per trade).
*   **FR-RMM-002: Stop Loss & Take Profit:** The software shall automatically set and manage Stop Loss and Take Profit levels for each trade.
*   **FR-RMM-003: Trailing Stop:** The software shall support trailing stop functionality to lock in profits as the market moves favorably.
*   **FR-RMM-004: Max Drawdown Protection:** The software shall include configurable parameters to stop trading if a predefined maximum drawdown is reached.
*   **FR-RMM-005: Daily/Weekly Loss Limits:** The software shall allow users to set daily and weekly maximum loss limits, halting trading if exceeded.

**3.3 Strategy Backtesting & Optimization**
*   **FR-STO-001: Historical Data Utilization:** The software shall utilize MT4's built-in historical data for robust backtesting of strategies.
*   **FR-STO-002: Backtesting Reports:** The software shall generate comprehensive backtesting reports, including performance metrics (e.g., profit factor, drawdown, number of trades).
*   **FR-STO-003: Strategy Optimization (Initial Consideration):** The software shall (ideally) leverage MT4's built-in optimizer for parameter optimization. (Further discussion needed on the extent of custom optimization features).
*   **FR-STO-004: Visual Mode Backtesting:** The software shall support visual mode backtesting for strategy validation and debugging.

**3.4 User Interface & Configuration (within MT4)**
*   **FR-UIC-001: Input Parameters:** The software shall expose all configurable strategy parameters (e.g., indicator settings, risk parameters) as external inputs to the Expert Advisor (EA).
*   **FR-UIC-002: On-Chart Display:** The software shall provide clear visual feedback on the chart, indicating current trade status, SL/TP levels, and relevant strategy information.
*   **FR-UIC-003: Account Information Display:** The software shall display key account metrics (e.g., equity, balance, margin, profit/loss) on the chart or in the MT4 "Experts" tab.
*   **FR-UIC-004: Error & Notification System:** The software shall provide clear notifications and error messages within the MT4 Expert tab or alerts for critical events (e.g., order rejection, connectivity issues).

**3.5 Connectivity & Reliability**
*   **FR-CNR-001: Broker Connectivity:** The software shall seamlessly integrate with any broker supported by the MT4 platform.
*   **FR-CNR-002: Reconnection Logic:** The software shall implement robust reconnection logic in case of temporary connectivity loss to the trading server.

---

### 4. Non-Functional Requirements

**4.1 Performance**
*   **NFR-PER-001: Latency:** Order execution latency shall be minimized, ideally within milliseconds of a signal generation, limited by broker and MT4 platform performance.
*   **NFR-PER-002: Resource Utilization:** The software shall have minimal CPU and memory footprint to avoid impacting MT4's performance or other EAs running concurrently.

**4.2 Reliability**
*   **NFR-REL-001: Uptime:** The software should operate continuously without crashes or critical errors, 24/5 when MT4 is running.
*   **NFR-REL-002: Error Handling:** Robust error handling mechanisms shall be implemented to gracefully handle unexpected situations (e.g., invalid parameters, server errors) without crashing.
*   **NFR-REL-003: Data Integrity:** All trading data and logs shall be accurately maintained and protected against corruption.

**4.3 Security**
*   **NFR-SEC-001: Data Protection:** The software shall not store sensitive user data outside of the MT4 platform. Any necessary persistent data will be stored securely within MT4's defined data directories.
*   **NFR-SEC-002: Code Obfuscation (Consideration):** For commercial distribution, consider basic code obfuscation techniques for intellectual property protection.

**4.4 Usability**
*   **NFR-USB-001: Ease of Installation:** The software shall be installable via standard MT4 EA installation procedures.
*   **NFR-USB-002: Configuration:** All user-configurable parameters shall be clearly labeled and intuitive to understand within the EA properties dialog.
*   **NFR-USB-003: Documentation:** Comprehensive documentation (user manual) shall be provided for installation, configuration, and troubleshooting.

**4.5 Maintainability**
*   **NFR-MTN-001: Code Modularity:** The MQL4 codebase should be modular and well-structured, allowing for easier future enhancements and bug fixes.
*   **NFR-MTN-002: Code Comments:** The code shall be thoroughly commented for clarity and maintainability.
*   **NFR-MTN-003: Logging:** The logging system shall provide sufficient detail for debugging and issue diagnosis.

**4.6 Scalability (MT4 Specific)**
*   **NFR-SCL-001: Multiple Instances:** The software should be capable of running multiple instances on different charts or MT4 terminals without conflict (assuming different strategy parameters).

---

### 5. User Stories

Here are some initial user stories to illustrate typical interactions with the software:

*   **As a retail trader, I want to easily install the software in my MT4 terminal, so I can start automating my trading.**
*   **As a trader, I want to input my desired lot size or risk percentage, so the software trades according to my risk tolerance.**
*   **As a trader, I want the software to automatically place stop loss and take profit orders for each trade, so my capital is protected and profits are secured.**
*   **As a trader, I want to see my current profit/loss and open positions displayed on the chart, so I can monitor my trading activity at a glance.**
*   **As a trader, I want to backtest my strategy against historical data, so I can verify its performance before going live.**
*   **As a cautious trader, I want the option to halt all trading if my daily loss limit is reached, so I can manage my overall risk.**
*   **As a trader with a proven strategy, I want the software to consistently execute trades based on my predefined MQL4 code, so I can avoid emotional decisions.**
*   **As a trader, I expect the software to handle temporary disconnections and reconnect without losing my current trade state, so my positions are managed continuously.**
*   **As a professional trader, I want detailed logs of all trade executions, so I can analyze past performance and troubleshoot any issues.**
*   **As a trader, I want clear alerts or notifications if there are any critical issues or order rejections, so I can take immediate action.**

---

### 6. Acceptance Criteria

**6.1 General**
*   The software successfully compiles and loads as an Expert Advisor (EA) in MT4.
*   All user input parameters are accessible and configurable through the EA properties window.
*   The software operates without generating critical errors or crashes within the MT4 journal or experts tab.
*   The software adheres to all defined non-functional requirements.

**6.2 Core Trading Engine**
*   **AC-CTE-001:** When a valid entry signal is generated, a market order (or specified order type) is placed within [X] milliseconds.
*   **AC-CTE-002:** When an exit signal is generated, the open position is closed successfully.
*   **AC-CTE-003:** Stop Loss and Take Profit levels are correctly set upon trade entry based on input parameters.
*   **AC-CTE-004:** The software correctly identifies and manages all open positions initiated by itself.
*   **AC-CTE-005:** All trade modifications (SL/TP adjustments, trailing stop movements) are executed accurately.

**6.3 Risk Management Module**
*   **AC-RMM-001:** Position size is calculated and applied correctly based on the chosen risk management method (fixed lot, % equity, etc.).
*   **AC-RMM-002:** Trailing Stop functionality correctly adjusts the Stop Loss level as price moves in favor of the trade.
*   **AC-RMM-003:** Trading halts when the configured maximum daily/weekly loss limit is reached, and an appropriate notification is issued.
*   **AC-RMM-004:** Trading halts when the configured maximum drawdown limit is reached, and an appropriate notification is issued.

**6.4 Strategy Backtesting & Optimization**
*   **AC-STO-001:** Backtesting of a strategy runs successfully on historical data within the MT4 Strategy Tester.
*   **AC-STO-002:** Backtesting reports accurately reflect performance metrics (e.g., total net profit, drawdown, profit factor, number of trades).
*   **AC-STO-003:** Visual mode backtesting accurately depicts trade entries, exits, and SL/TP movements on the chart.

**6.5 User Interface & Configuration**
*   **AC-UIC-001:** All on-chart information (trade status, SL/TP) is updated in real-time and is legible.
*   **AC-UIC-002:** All critical alerts and error messages are displayed clearly in the MT4 Experts tab.

---

### 7. Technical Considerations

**7.1 Platform:** MetaTrader 4 (MT4)
**7.2 Programming Language:** MQL4
**7.3 Code Structure:**
    *   Modular design using functions, potentially custom classes/structs where MQL4 allows.
    *   Clear separation of concerns (e.g., signal generation logic, order management, risk management).
    *   Extensive use of `#property` directives for EA identification and settings.
**7.4 Libraries/Dependencies:** Primarily built-in MQL4 functions and standard libraries. Avoid external DLLs unless absolutely necessary and justified for security and compatibility.
**7.5 Data Storage:** Utilize MT4's global variables or file operations for persistent data if required (e.g., tracking daily performance limits across restarts).
**7.6 Error Handling:** Implement robust `GetLastError()` checks and appropriate handling for trading operations.
**7.7 Timeframes:** The EA should be able to operate on any standard MT4 timeframe, but strategies may be optimized for specific timeframes.
**7.8 Broker Compatibility:** Efforts should be made to ensure compatibility with a wide range of MT4 brokers, accounting for potential minor differences in symbol naming or execution.
**7.9 Testing Environment:** Development and testing will primarily occur in the MT4 Strategy Tester and demo accounts.
**7.10 Version Control:** Utilize a version control system (e.g., Git) for collaborative development and tracking changes.

---

### 8. Timeline and Milestones

**Phase 1: Planning & Setup (Weeks 1-2)**
*   **Milestone 1.1:** Finalize detailed strategy specifications (external input to this PRD).
*   **Milestone 1.2:** Set up development environment (MT4, MQL4 editor, version control).
*   **Milestone 1.3:** Complete initial architectural design for MQL4 code structure.

**Phase 2: Core Trading Engine Development (Weeks 3-6)**
*   **Milestone 2.1:** Implement basic market data retrieval and order placement functionalities.
*   **Milestone 2.2:** Develop initial strategy logic based on predefined rules.
*   **Milestone 2.3:** Implement basic position management (tracking open trades, P/L).
*   **Milestone 2.4:** Unit testing of core engine functions on demo account.

**Phase 3: Risk Management & Backtesting Integration (Weeks 7-10)**
*   **Milestone 3.1:** Integrate position sizing, SL/TP, and trailing stop functionalities.
*   **Milestone 3.2:** Implement daily/weekly loss limits and maximum drawdown protection.
*   **Milestone 3.3:** Integrate with MT4 Strategy Tester for basic backtesting.
*   **Milestone 3.4:** Generate initial backtesting reports.

**Phase 4: UI, Error Handling & Refinement (Weeks 11-14)**
*   **Milestone 4.1:** Develop on-chart display elements and user notifications.
*   **Milestone 4.2:** Implement comprehensive error handling and logging.
*   **Milestone 4.3:** Conduct thorough testing of all functional and non-functional requirements.
*   **Milestone 4.4:** Refine code for performance and stability.

**Phase 5: Documentation & Release Preparation (Weeks 15-16)**
*   **Milestone 5.1:** Prepare user manual and installation guide.
*   **Milestone 5.2:** Final internal review and quality assurance.
*   **Milestone 5.3:** Prepare for initial deployment (e.g., beta testing with selected users, if applicable).

---
