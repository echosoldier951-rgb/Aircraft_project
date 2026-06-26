CREATE TABLE IF NOT EXISTS flights (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20) UNIQUE NOT NULL,
    aircraft_status VARCHAR(100) NOT NULL,
    passenger_boarding_number INTEGER NOT NULL,
    fueling VARCHAR(50) NOT NULL,
    door_state VARCHAR(50) NOT NULL,
    push_back_time VARCHAR(20) NOT NULL
);

INSERT INTO flights (
    flight_number,
    aircraft_status,
    passenger_boarding_number,
    fueling,
    door_state,
    push_back_time
)
VALUES
(
    'AB1234',
    'Ready for departure',
    128,
    'Completed',
    'Closed',
    '13:45'
),
(
    'CD5678',
    'Check-in now open',
    42,
    'Pending',
    'Open',
    '06:30'
),
(
    'EF9012',
    'Boarding soon',
    156,
    'Completed',
    'Open',
    '07:15'
),
(
    'GH3456',
    'Now boarding',
    87,
    'Completed',
    'Open',
    '08:00'
),
(
    'JK7890',
    'Final boarding call',
    173,
    'Completed',
    'Open',
    '08:45'
),
(
    'LM1235',
    'Delayed due to weather',
    94,
    'Paused',
    'Open',
    '09:30'
),
(
    'NP6789',
    'Gate change - Proceed to Gate B12',
    61,
    'Completed',
    'Open',
    '10:15'
),
(
    'QR2468',
    'Ready for boarding',
    211,
    'Completed',
    'Open',
    '11:00'
),
(
    'ST1357',
    'Flight on schedule',
    37,
    'Completed',
    'Open',
    '11:45'
),
(
    'UV9753',
    'Estimated departure in 20 minutes',
    52,
    'Completed',
    'Closing',
    '12:30'
),
(
    'WX8642',
    'Boarding complete',
    143,
    'Completed',
    'Closed',
    '13:15'
),
(
    'YZ7531',
    'Ready for departure',
    29,
    'Completed',
    'Closed',
    '14:00'
),
(
    'AA4826',
    'Departed',
    118,
    'Completed',
    'Closed',
    '14:45'
),
(
    'BB9174',
    'Arrived',
    164,
    'Completed',
    'Closed',
    '15:30'
),
(
    'CC6401',
    'Baggage claim available',
    189,
    'Completed',
    'Closed',
    '16:15'
),
(
    'DD3589',
    'Please proceed to security',
    76,
    'Pending',
    'Open',
    '17:00'
)
ON CONFLICT (flight_number) DO NOTHING;