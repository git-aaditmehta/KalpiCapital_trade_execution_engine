#!/usr/bin/env python3
"""
Example usage of Zerodha integration.

This script demonstrates how to use the Zerodha broker integration
for authentication, fetching holdings, and placing orders.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.services.broker_service import broker_service
from app.models.portfolio import TradeInstruction, TradeAction


async def main():
    """Main example function."""
    print("🚀 Zerodha Integration Example")
    print("=" * 50)
    
    # Step 1: Initiate OAuth flow
    print("\n1️⃣ Initiating Zerodha OAuth flow...")
    try:
        auth_response = await broker_service.connect_zerodha()
        if not auth_response.authenticated:
            print(f"🔗 Please visit: {auth_response.login_url}")
            print("📝 After login, you'll get a request_token")
            
            # For demo purposes, we'll skip the actual OAuth flow
            request_token = input("Enter request_token (or press Enter to skip): ").strip()
            if not request_token:
                print("⚠️ Skipping OAuth flow for demo")
                return
        else:
            print("✅ Already authenticated")
            request_token = None
    except Exception as e:
        print(f"❌ OAuth initiation failed: {e}")
        return
    
    # Step 2: Handle OAuth callback
    if request_token:
        print("\n2️⃣ Handling OAuth callback...")
        try:
            callback_response = await broker_service.zerodha_callback(request_token)
            if callback_response.authenticated:
                access_token = callback_response.session_token
                user_id = callback_response.user_id
                print(f"✅ Connected to Zerodha as {user_id}")
            else:
                print(f"❌ Authentication failed: {callback_response.message}")
                return
        except Exception as e:
            print(f"❌ Callback handling failed: {e}")
            return
    else:
        # Use existing token from environment for demo
        access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        if not access_token:
            print("❌ No access token available. Set ZERODHA_ACCESS_TOKEN in .env")
            return
        print(f"✅ Using access token from environment")
    
    # Step 3: Fetch holdings
    print("\n3️⃣ Fetching holdings...")
    try:
        holdings = await broker_service.get_holdings("zerodha", access_token)
        print(f"📊 Found {len(holdings)} holdings:")
        for holding in holdings[:5]:  # Show first 5
            print(f"  • {holding.symbol}: {holding.quantity} shares @ ₹{holding.average_price}")
        if len(holdings) > 5:
            print(f"  ... and {len(holdings) - 5} more")
    except Exception as e:
        print(f"❌ Failed to fetch holdings: {e}")
        return
    
    # Step 4: Place a sample order (read-only)
    print("\n4️⃣ Placing sample order...")
    print("⚠️ This is a DEMO - no actual order will be placed")
    
    sample_instruction = TradeInstruction(
        action=TradeAction.BUY,
        symbol="RELIANCE",
        quantity=1,
        exchange="NSE",
        order_type="MARKET"
    )
    
    print(f"📈 Sample order: {sample_instruction.action.value} {sample_instruction.quantity} {sample_instruction.symbol}")
    
    # Uncomment the following lines to place a real order:
    # try:
    #     result = await broker_service.place_order("zerodha", access_token, sample_instruction)
    #     if result.status.value == "EXECUTED":
    #         print(f"✅ Order placed successfully: {result.order_id}")
    #     else:
    #         print(f"❌ Order failed: {result.message}")
    # except Exception as e:
    #     print(f"❌ Order placement failed: {e}")
    
    # Step 5: Execute multiple trades (demo)
    print("\n5️⃣ Executing multiple trades (demo)...")
    sample_trades = [
        TradeInstruction(action=TradeAction.BUY, symbol="RELIANCE", quantity=1),
        TradeInstruction(action=TradeAction.SELL, symbol="TCS", quantity=1),
    ]
    
    print(f"📊 Sample trades: {len(sample_trades)} trades")
    for trade in sample_trades:
        print(f"  • {trade.action.value} {trade.quantity} {trade.symbol}")
    
    # Uncomment the following lines to execute real trades:
    # try:
    #     summary = await broker_service.execute_trades("zerodha", access_token, sample_trades)
    #     print(f"✅ Execution complete: {summary.successful}/{summary.total_orders} successful")
    # except Exception as e:
    #     print(f"❌ Trade execution failed: {e}")
    
    # Step 6: Check order status (demo)
    print("\n6️⃣ Checking order status (demo)...")
    sample_order_id = "1234567890"
    print(f"🔍 Checking status for order: {sample_order_id}")
    
    # Uncomment the following lines to check real order status:
    # try:
    #     result = await broker_service.get_order_status("zerodha", access_token, sample_order_id)
    #     print(f"📊 Order {result.order_id} status: {result.status.value}")
    # except Exception as e:
    #     print(f"❌ Order status check failed: {e}")
    
    print("\n✅ Example completed successfully!")
    print("\n📝 Notes:")
    print("  • Uncomment the real order sections to test actual trading")
    print("  • Ensure you have sufficient funds for real orders")
    print("  • Only place orders during market hours (9:15 AM - 3:30 PM IST)")
    print("  • Start with small quantities for testing")


if __name__ == "__main__":
    print("🔧 Zerodha Integration Example")
    print("📋 Prerequisites:")
    print("  • Set ZERODHA_API_KEY and ZERODHA_API_SECRET in .env")
    print("  • Or set ZERODHA_ACCESS_TOKEN for direct testing")
    print("  • Install dependencies: pip install kiteconnect python-dotenv")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example interrupted by user")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("🔧 Please check your configuration and try again")
