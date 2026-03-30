#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Mark Unreachable Devices as Inactive                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "This will mark 13 devices that failed DNS resolution as 'inactive'"
echo "They will remain in the database but won't be used for collection."
echo ""
echo "Devices to mark inactive:"
echo "  - snpsrx1600a"
echo "  - snpsrx4300b"
echo "  - snpsrx1600b"
echo "  - esst-srv66-http01"
echo "  - esst-srv61-http01"
echo "  - snpsrx1500aa"
echo "  - snpsrx4600j"
echo "  - snpsrx4120c"
echo "  - snpsrx4700b-proto"
echo "  - snpsrx345d"
echo "  - snpsrx340k"
echo "  - snpsrx300y"
echo "  - snpsrx5600q"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    docker exec longevity-db psql -U postgres -d longevity -c "
    UPDATE devices 
    SET status = 'inactive', updated_at = NOW()
    WHERE name IN (
      'snpsrx1600a',
      'snpsrx4300b',
      'snpsrx1600b',
      'esst-srv66-http01',
      'esst-srv61-http01',
      'snpsrx1500aa',
      'snpsrx4600j',
      'snpsrx4120c',
      'snpsrx4700b-proto',
      'snpsrx345d',
      'snpsrx340k',
      'snpsrx300y',
      'snpsrx5600q'
    );
    "
    
    echo ""
    echo "✓ Devices marked as inactive"
    echo ""
    echo "Current device status:"
    docker exec longevity-db psql -U postgres -d longevity -c "
    SELECT status, COUNT(*) as count 
    FROM devices 
    GROUP BY status 
    ORDER BY status;
    "
    
    echo ""
    echo "Active devices:"
    docker exec longevity-db psql -U postgres -d longevity -c "
    SELECT name, device_type, routing 
    FROM devices 
    WHERE status = 'active' 
    ORDER BY device_type, name;
    "
else
    echo "Cancelled."
fi
