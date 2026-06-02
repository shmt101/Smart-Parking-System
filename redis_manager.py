import time
import sys
import redis

class RedisParkingManager:
    def __init__(self, host="localhost", port=6379):
        try:
            self.r = redis.Redis(host=host, port=port, decode_responses=True)
            self.r.ping()
        except Exception as e:
            print(f"❌ Redis Connection Error: {e}")
            sys.exit(1)

    def register_zone(self, zone_id, zone_name, total_spaces):
        """Registers parking assets via modular Hashes and descriptive sets."""
        start_time = time.perf_counter()
        if int(total_spaces) <= 0:
            raise ValueError("Total spaces must be a positive number.")

        pipe = self.r.pipeline()
        
        # Meta storage for zone configuration
        pipe.hset(f"zone_meta:{zone_id}", mapping={
            "zone_name": zone_name,
            "total_spaces": total_spaces
        })
        pipe.sadd("global_zones_set", zone_id)

        for i in range(1, int(total_spaces) + 1):
            space_id = f"SP_{zone_id}_{i:03d}"
            space_type = "EV_Charging" if i % 5 == 0 else "Standard"
            
            # Map tracking elements
            pipe.hset(f"parking_space:{space_id}", mapping={
                "space_id": space_id,
                "type": space_type,
                "status": "vacant",
                "zone_id": zone_id
            })
            # Track index boundaries inside sets
            pipe.sadd(f"zone_spaces:{zone_id}", space_id)
            pipe.sadd(f"zone_vacant:{zone_id}", space_id)

        pipe.execute()
        return time.perf_counter() - start_time

    def get_realtime_availability(self):
        """Reconstructs the multi-tiered zone layout from flat Key-Value caches."""
        start_time = time.perf_counter()
        zone_ids = self.r.smembers("global_zones_set")
        
        structured_output = []
        for zone_id in zone_ids:
            meta = self.r.hgetall(f"zone_meta:{zone_id}")
            if not meta:
                continue
                
            space_ids = self.r.smembers(f"zone_spaces:{zone_id}")
            spaces_list = []
            for sp_id in sorted(space_ids):
                spaces_list.append(self.r.hgetall(f"parking_space:{sp_id}"))

            structured_output.append({
                "_id": zone_id,
                "zone_name": meta.get("zone_name"),
                "total_spaces": int(meta.get("total_spaces", 0)),
                "parking_spaces": spaces_list
            })

        elapsed = time.perf_counter() - start_time
        return structured_output, elapsed

    def update_parking_status(self, zone_id, space_id, new_status):
        """Alters target status flags dynamically and creates entry/exit stream timelines."""
        if new_status not in ["vacant", "occupied"]:
            raise ValueError("Status must be either 'vacant' or 'occupied'.")

        if not self.r.exists(f"parking_space:{space_id}"):
            raise LookupError(f"Space {space_id} does not exist.")

        start_time = time.perf_counter()
        pipe = self.r.pipeline()
        
        pipe.hset(f"parking_space:{space_id}", "status", new_status)
        
        # Synchronize categorical index sets
        if new_status == "vacant":
            pipe.sadd(f"zone_vacant:{zone_id}", space_id)
        else:
            pipe.srem(f"zone_vacant:{zone_id}", space_id)

        # Log to event counter tracking
        if new_status == "occupied":
            pipe.hincrby("analytics:zone_demands", zone_id, 1)

        pipe.execute()
        return time.perf_counter() - start_time

    def get_high_demand_zones(self):
        """Extracts increment counts tracking space occupancy frequency."""
        start_time = time.perf_counter()
        raw_demands = self.r.hgetall("analytics:zone_demands")
        
        formatted = []
        for z_id, score in raw_demands.items():
            formatted.append({"_id": z_id, "total_entries": int(score)})
            
        # Sort descending to isolate hot spots
        formatted.sort(key=lambda x: x["total_entries"], reverse=True)
        
        elapsed = time.perf_counter() - start_time
        return formatted, elapsed

    def remove_zone(self, zone_id):
        """Deletes hashes, clear tracking lists, and purges target sets entirely."""
        if not self.r.sismember("global_zones_set", zone_id):
            raise LookupError(f"Zone {zone_id} does not exist.")

        start_time = time.perf_counter()
        space_ids = self.r.smembers(f"zone_spaces:{zone_id}")
        
        pipe = self.r.pipeline()
        for sp_id in space_ids:
            pipe.delete(f"parking_space:{sp_id}")
            
        pipe.delete(f"zone_spaces:{zone_id}")
        pipe.delete(f"zone_vacant:{zone_id}")
        pipe.delete(f"zone_meta:{zone_id}")
        pipe.srem("global_zones_set", zone_id)
        pipe.hdel("analytics:zone_demands", zone_id)
        
        pipe.execute()
        return time.perf_counter() - start_time

    def get_memory_usage(self):
        """Parses active runtime allocation footprints directly out of Redis INFO commands."""
        memory_info = self.r.info("memory")
        # Returns memory converted to Kilobytes
        return memory_info.get("used_memory", 0) / 1024