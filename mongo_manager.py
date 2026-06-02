import time
import sys
from pymongo import MongoClient

class MongoParkingManager:
    def __init__(self, uri="mongodb://localhost:27017/"):
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            self.db = self.client["smart_parking_db"]
            # Trigger connection check
            self.client.server_info()
        except Exception as e:
            print(f"❌ MongoDB Connection Error: {e}")
            sys.exit(1)

    def register_zone(self, zone_id, zone_name, total_spaces):
        """Creates a new parking zone with an embedded array of empty spaces."""
        start_time = time.perf_counter()
        
        # Validate inputs
        if int(total_spaces) <= 0:
            raise ValueError("Total spaces must be a positive number.")

        # Build embedded array of spaces
        spaces = []
        for i in range(1, int(total_spaces) + 1):
            spaces.append({
                "space_id": f"SP_{zone_id}_{i:03d}",
                "type": "EV_Charging" if i % 5 == 0 else "Standard",
                "status": "vacant"
            })

        zone_document = {
            "_id": zone_id,
            "zone_name": zone_name,
            "total_spaces": int(total_spaces),
            "parking_spaces": spaces
        }

        self.db.parking_zones.insert_one(zone_document)
        return time.perf_counter() - start_time

    def get_realtime_availability(self):
        """Reads and formats real-time space status across all zones."""
        start_time = time.perf_counter()
        zones = list(self.db.parking_zones.find({}))
        elapsed = time.perf_counter() - start_time
        return zones, elapsed

    def update_parking_status(self, zone_id, space_id, new_status):
        """Atomically updates a nested space status and logs historical transitions."""
        if new_status not in ["vacant", "occupied"]:
            raise ValueError("Status must be either 'vacant' or 'occupied'.")
            
        start_time = time.perf_counter()

        # Step 1: Update the embedded sub-document array status
        result = self.db.parking_zones.update_one(
            {"_id": zone_id, "parking_spaces.space_id": space_id},
            {"$set": {"parking_spaces.$.status": new_status}}
        )

        if result.matched_count == 0:
            raise LookupError(f"Zone {zone_id} or Space {space_id} not found.")

        # Step 2: Log historical tracking events if space becomes occupied or vacant
        event_log = {
            "zone_id": zone_id,
            "space_id": space_id,
            "action": "entry" if new_status == "occupied" else "exit",
            "timestamp": time.time()
        }
        self.db.parking_events.insert_one(event_log)

        return time.perf_counter() - start_time

    def get_high_demand_zones(self):
        """Aggregates event collections to pinpoint high usage frequency by zone."""
        start_time = time.perf_counter()
        pipeline = [
            {"$match": {"action": "occupied"}},
            {"$group": {"_id": "$zone_id", "total_entries": {"$sum": 1}}},
            {"$sort": {"total_entries": -1}}
        ]
        results = list(self.db.parking_events.aggregate(pipeline))
        elapsed = time.perf_counter() - start_time
        return results, elapsed

    def remove_zone(self, zone_id):
        """Deletes an entire zone and purges related transactional history logs."""
        start_time = time.perf_counter()
        
        # CRUD: Delete zone
        zone_result = self.db.parking_zones.delete_one({"_id": zone_id})
        if zone_result.deleted_count == 0:
            raise LookupError(f"Zone {zone_id} does not exist.")
            
        # Clean up events cascadingly
        self.db.parking_events.delete_many({"zone_id": zone_id})
        
        return time.perf_counter() - start_time

    def get_memory_usage(self):
        """Returns physical database memory footprint in Kilobytes."""
        stats = self.db.command("dbStats")
        # return dataSize + indexSize combined
        return (stats.get("dataSize", 0) + stats.get("indexSize", 0)) / 1024