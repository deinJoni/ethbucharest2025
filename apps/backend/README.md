# Wallet API Documentation

This document provides information about the wallet endpoints available in the API.

## Endpoints

### Create or Get Wallet

- **URL**: `/wallets/`
- **Method**: `POST`
- **Description**: Creates a new wallet or returns an existing one if the address already exists
- **Request Body**:
  ```json
  {
    "address": "0x123abc..." // Ethereum wallet address
  }
  ```
- **Response**: Wallet object with details
  ```json
  {
    "id": 1,
    "address": "0x123abc...",
    "created_at": "2023-01-01T00:00:00"
  }
  ```

### Get Wallet by Address

- **URL**: `/wallets/{address}`
- **Method**: `GET`
- **Description**: Retrieves information about a specific wallet
- **Parameters**:
  - `address` (path parameter): The wallet address to look up
- **Response**: Wallet object with details
- **Error Response**: 404 Not Found if the wallet does not exist

### Update Wallet Risk Profile

- **URL**: `/wallets/risk-profile`
- **Method**: `PUT`
- **Description**: Updates the risk profile for a specific wallet
- **Request Body**:
  ```json
  {
    "address": "0x123abc...",
    "risk_profile": "High Risk, High Reward"
  }
  ```
- **Valid risk_profile values**:
  - `"High Risk, High Reward"` (for HIGH_RISK)
  - `"Balanced & Strategic"` (for BALANCED)
  - `"Safe & Steady"` (for SAFE)
- **Response**: Updated wallet object with details
- **Error Response**: 404 Not Found if the wallet does not exist

## Models

The API uses the following data models:

- `WalletCreate`: Contains the wallet address to create or look up
- `WalletResponse`: Contains wallet details returned by the API

## Usage Example

```bash
# Create or get a wallet
curl -X POST -H "Content-Type: application/json" \
  -d '{"address": "0x123abc..."}' \
  http://localhost:8000/wallets/

# Get wallet by address
curl -X GET http://localhost:8000/wallets/0x123abc...

# Update wallet risk profile
curl -X PUT -H "Content-Type: application/json" \
  -d '{"address": "0x123abc...", "risk_profile": "Safe & Steady"}' \
  http://localhost:8000/wallets/risk-profile
```
