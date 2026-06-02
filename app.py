import os
from mongo_manager import MongoParkingManager
from redis_manager import RedisParkingManager

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_loop():
    clear_screen()
    print("==============================================")
    print("  MIT212 SMART CITY SUSTAINABLE PARKING SYSTEM ")
    print("==============================================")
    print("Select Database Backend Engine to Evaluate:")
    print("1) MongoDB (Document-Oriented Array Paradigm)")
    print("2) Redis   (In-Memory Key-Value / Set Cache)")
    print("==============================================")
    
    choice = input("Select Option (1-2): ").strip()
    if choice == "1":
        db = MongoParkingManager()
        engine_name = "MongoDB Engine"
    elif choice == "2":
        db = RedisParkingManager()
        engine_name = "Redis Cache Engine"
    else:
        print("❌ Invalid entry. Defaulting to MongoDB.")
        db = MongoParkingManager()
        engine_name = "MongoDB Engine"

    while True:
        clear_screen()
        print(f"⚙️ Active Backend Context: [{engine_name}]")
        print("==================================================")
        print("1. Define & Register Parking Zone (Create)")
        print("2. View Real-time Parking Status  (Read)")
        print("3. Update Parking Space Status     (Update)")
        print("4. Identify High-Demand Areas      (Analytics)")
        print("5. Decommission Parking Zone       (Delete)")
        print("6. Read Active Memory Footprint   (Metrics)")
        print("7. Switch Database Engine / Exit")
        print("==================================================")
        
        op = input("Choose Action (1-7): ").strip()

        try:
            if op == "1":
                z_id = input("Enter unique Zone ID (e.g., ZONE_CBD_01): ").strip()
                z_name = input("Enter descriptive Zone Name (e.g., North Block): ").strip()
                count = input("Enter Total Parking Spaces to deploy: ").strip()
                
                latency = db.register_zone(z_id, z_name, count)
                print(f"\n✅ Zone Registered Successfully! Operation Latency: {latency:.6f} seconds.")

            elif op == "2":
                zones, latency = db.get_realtime_availability()
                print(f"\n--- REAL-TIME URBAN INFRASTRUCTURE MAP (Fetch Latency: {latency:.6f}s) ---")
                if not zones:
                    print("No zones deployed yet.")
                for z in zones:
                    print(f"\n📍 Zone: {z['zone_name']} [{z['_id']}] | Capacity: {z['total_spaces']} spots")
                    for sp in z['parking_spaces']:
                        status_emoji = "🚗 [OCCUPIED]" if sp['status'] == "occupied" else "🟢 [VACANT]"
                        print(f"  └─ Space: {sp['space_id']} | Type: {sp['type']:<12} | Status: {status_emoji}")

            elif op == "3":
                z_id = input("Enter Zone ID: ").strip()
                sp_id = input("Enter Space ID: ").strip()
                print("1) Mark as Occupied (Vehicle Arrival)\n2) Mark as Vacant (Vehicle Departure)")
                st_choice = input("Select Status update: ").strip()
                status_str = "occupied" if st_choice == "1" else "vacant"
                
                latency = db.update_parking_status(z_id, sp_id, status_str)
                print(f"\n✅ Status updated atomically! Latency: {latency:.6f} seconds.")

            elif op == "4":
                metrics, latency = db.get_high_demand_zones()
                print(f"\n--- SUSTAINABLE URBAN DEMAND ANALYSIS (Query Latency: {latency:.6f}s) ---")
                if not metrics:
                    print("No occupancy traffic recorded yet.")
                for item in metrics:
                    print(f"▪️ Zone Reference ID: {item['_id']:<15} | Total Vehicle Arrivals logged: {item['total_entries']}")

            elif op == "5":
                z_id = input("Enter Zone ID to wipe: ").strip()
                latency = db.remove_zone(z_id)
                print(f"\n✅ Zone {z_id} removed safely. Operation Latency: {latency:.6f} seconds.")

            elif op == "6":
                print(f"\n📊 Current Database Ram/Storage Footprint: {db.get_memory_usage():.2f} KB")

            elif op == "7":
                print("\nReturning to backend engine selection menu...")
                break
            else:
                print("❌ Invalid command entry option.")

        except Exception as e:
            print(f"\n⚠️ Error Handling Safeguard triggered: {e}")

        input("\nPress Enter to return to main menu interface...")

if __name__ == "__main__":
    while True:
        main_loop()