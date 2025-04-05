# ETH Bucharest 2025 Project - "let me know"

A web3 application that provides portfolio management opinions about crypto assets based on AI agent analysis and user preferences. Developed during ETH Bucharest 2025.

## Project Overview

"let me know" helps crypto investors make informed decisions by providing AI-powered insights on when to buy, hold, or sell their assets. The platform uses multiple AI agents with different trading strategies to analyze tokens and provide recommendations based on the user's risk preferences.

## Features

- **Connect Wallet**: Easily connect your crypto wallet using Coinbase Wallet or other providers
- **Token Analysis**: Get detailed analysis for your tokens from multiple AI perspectives
- **Risk Profiling**: Set your risk preference profile (High Risk/High Reward, Balanced & Strategic, or Safe & Steady)
- **AI Trading Agents**: Multiple specialized AI agents provide diverse investment perspectives:
  - Bounce Hunter
  - Crypto Oracle
  - Momentum Quant Agent
  - Simple Moving Average (SMA) Agent
  - Portfolio Manager Agent
- **Token Metrics Integration**: Real-time token data and metrics

## Tech Stack

### Frontend
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Coinbase OnchainKit
- Wagmi for wallet connection
- Moralis SDK for blockchain data
- Recharts for data visualization
- Zustand for state management
- Axios for API requests

### Backend
- FastAPI (Python)
- Langchain for AI agent orchestration
- Token Metrics API integration
- SQLite database
- Multiple AI agents with specialized trading strategies

## Getting Started

### Prerequisites
- Node.js (v16+)
- Python 3.9+
- npm, yarn, or pnpm

### Backend Setup
1. Navigate to the backend directory:
   ```
   cd apps/backend
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit `.env` with your API keys and configuration

5. Run the server:
   ```
   python main.py
   ```
   The API will be available at http://localhost:8000

### Frontend Setup
1. Navigate to the frontend directory:
   ```
   cd apps/frontend
   ```

2. Install dependencies:
   ```
   npm install
   # or
   yarn install
   # or
   pnpm install
   ```

3. Set up environment variables:
   ```
   cp .env.example .env
   ```
   Edit `.env` with your API configuration

4. Run the development server:
   ```
   npm run dev
   # or
   yarn dev
   # or
   pnpm dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) with your browser to see the application

## API Endpoints

### Wallet Endpoints
- `POST /wallets/`: Create or get a wallet
- `GET /wallets/{address}`: Get wallet by address
- `PUT /wallets/risk-profile`: Update wallet risk profile

### Agent Endpoints
- `/api/v1/agents/`: Access to various AI trading agents
- `/api/v1/agents/analysis/{token}`: Get analysis for a specific token

### Token Metrics
- `/token-metrics/`: Access token metrics data
