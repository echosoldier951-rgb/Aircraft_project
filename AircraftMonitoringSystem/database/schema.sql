DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS flights;

CREATE TABLE flights (
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
('AB1234', 'Ready for departure', 128, 'Completed', 'Closed', '13:45'),
('CD5678', 'Check-in now open', 42, 'Pending', 'Open', '06:30'),
('EF9012', 'Boarding soon', 156, 'Completed', 'Open', '07:15'),
('GH3456', 'Now boarding', 87, 'Completed', 'Open', '08:00'),
('JK7890', 'Final boarding call', 173, 'Completed', 'Open', '08:45'),
('LM1235', 'Delayed due to weather', 94, 'Paused', 'Open', '09:30'),
('NP6789', 'Gate change - Proceed to Gate B12', 61, 'Completed', 'Open', '10:15'),
('QR2468', 'Ready for boarding', 211, 'Completed', 'Open', '11:00'),
('ST1357', 'Flight on schedule', 37, 'Completed', 'Open', '11:45'),
('UV9753', 'Estimated departure in 20 minutes', 52, 'Completed', 'Closing', '12:30'),
('WX8642', 'Boarding complete', 143, 'Completed', 'Closed', '13:15'),
('YZ7531', 'Ready for departure', 29, 'Completed', 'Closed', '14:00'),
('AA4826', 'Departed', 118, 'Completed', 'Closed', '14:45'),
('BB9174', 'Arrived', 164, 'Completed', 'Closed', '15:30'),
('CC6401', 'Baggage claim available', 189, 'Completed', 'Closed', '16:15'),
('DD3589', 'Please proceed to security', 76, 'Pending', 'Open', '17:00');

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20) UNIQUE NOT NULL,
    autopilot_status VARCHAR(20) NOT NULL,
    cabin_pressure DECIMAL(4,2) NOT NULL,
    wifi_usage INTEGER NOT NULL
);

INSERT INTO events (
    flight_number,
    autopilot_status,
    cabin_pressure,
    wifi_usage
)
VALUES
('AB1234', 'ON', 10.50, 124),
('CD5678', 'OFF', 9.80, 48),
('EF9012', 'ON', 10.20, 89),
('GH3456', 'ON', 10.60, 105),
('JK7890', 'ON', 10.10, 132),
('LM1235', 'OFF', 9.50, 41),
('NP6789', 'ON', 10.40, 77),
('QR2468', 'ON', 10.30, 150),
('ST1357', 'OFF', 9.70, 33),
('UV9753', 'ON', 10.00, 58),
('WX8642', 'ON', 10.80, 112),
('YZ7531', 'OFF', 9.90, 27),
('AA4826', 'ON', 10.25, 94),
('BB9174', 'ON', 10.55, 138),
('CC6401', 'OFF', 9.60, 65),
('DD3589', 'ON', 10.15, 84);