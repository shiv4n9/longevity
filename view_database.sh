#!/bin/bash

echo "=== Longevity Database Viewer ==="
echo ""
echo "Choose an option:"
echo "1. List all tables"
echo "2. View devices"
echo "3. View latest metrics (with platform)"
echo "4. View metrics count per device"
echo "5. Interactive psql session"
echo "6. View specific device metrics"
echo ""
read -p "Enter option (1-6): " option

case $option in
  1)
    echo ""
    echo "=== All Tables ==="
    docker exec -it longevity-db psql -U postgres -d longevity -c "\dt"
    ;;
  2)
    echo ""
    echo "=== All Devices ==="
    docker exec -it longevity-db psql -U postgres -d longevity -c "SELECT id, name, hostname, device_type, status FROM devices ORDER BY name;"
    ;;
  3)
    echo ""
    echo "=== Latest Metrics (with Platform) ==="
    docker exec -it longevity-db psql -U postgres -d longevity -c "
      SELECT 
        d.name, 
        m.platform,
        m.model,
        m.cpu_usage, 
        m.memory_usage,
        m.flow_session_current,
        m.has_core_dumps,
        m.timestamp 
      FROM metrics m 
      JOIN devices d ON m.device_id = d.id 
      ORDER BY m.timestamp DESC 
      LIMIT 20;
    "
    ;;
  4)
    echo ""
    echo "=== Metrics Count Per Device ==="
    docker exec -it longevity-db psql -U postgres -d longevity -c "
      SELECT 
        d.name, 
        COUNT(m.id) as total_metrics,
        MAX(m.timestamp) as last_collection,
        MAX(m.platform) as platform
      FROM devices d 
      LEFT JOIN metrics m ON d.id = m.device_id 
      GROUP BY d.name 
      ORDER BY d.name;
    "
    ;;
  5)
    echo ""
    echo "=== Interactive psql Session ==="
    echo "Type 'exit' or '\q' to quit"
    echo ""
    docker exec -it longevity-db psql -U postgres -d longevity
    ;;
  6)
    echo ""
    read -p "Enter device name (e.g., snpsrx4300a): " device_name
    echo ""
    echo "=== Metrics for $device_name ==="
    docker exec -it longevity-db psql -U postgres -d longevity -c "
      SELECT 
        m.timestamp,
        m.platform,
        m.model,
        m.cpu_usage,
        m.memory_usage,
        m.flow_session_current,
        m.has_core_dumps
      FROM metrics m 
      JOIN devices d ON m.device_id = d.id 
      WHERE d.name = '$device_name'
      ORDER BY m.timestamp DESC 
      LIMIT 10;
    "
    ;;
  *)
    echo "Invalid option"
    ;;
esac
