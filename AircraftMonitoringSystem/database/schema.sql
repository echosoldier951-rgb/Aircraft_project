DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS flights;


-- FLIGHTS TABLE

CREATE TABLE flights (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20) UNIQUE NOT NULL,
    simple_status VARCHAR(50) NOT NULL,
    detailed_status VARCHAR(100) NOT NULL,
    passenger_boarding_number INTEGER NOT NULL,
    fueling VARCHAR(50) NOT NULL,
    door_state VARCHAR(50) NOT NULL,
    push_back_time TIME NOT NULL
);

INSERT INTO flights (
    flight_number,
    simple_status,
    detailed_status,
    passenger_boarding_number,
    fueling,
    door_state,
    push_back_time
)
VALUES

-- PARKED
('AB1234', 'Parked', 'Check-in now open', 128, 'Pending', 'Open', '13:45'),
('CD5678', 'Parked', 'Boarding soon', 42, 'Completed', 'Open', '06:30'),
('EF9012', 'Parked', 'Now boarding', 156, 'Completed', 'Open', '07:15'),
('GH3456', 'Parked', 'Delayed due to weather', 87, 'Paused', 'Open', '08:00'),

-- TAXIING
('JK7890', 'Taxiing', 'Ready for departure', 173, 'Completed', 'Closed', '08:45'),
('LM1235', 'Taxiing', 'Boarding complete', 94, 'Completed', 'Closed', '09:30'),
('NP6789', 'Taxiing', 'Estimated departure in 20 minutes', 61, 'Completed', 'Closing', '10:15'),
('QR2468', 'Taxiing', 'Pushback in progress', 211, 'Completed', 'Closed', '11:00'),

-- TAKEOFF/LANDING
('ST1357', 'Takeoff/Landing', 'Departed', 37, 'Completed', 'Closed', '11:45'),
('UV9753', 'Takeoff/Landing', 'Takeoff clearance received', 52, 'Completed', 'Closed', '12:30'),
('WX8642', 'Takeoff/Landing', 'Final approach', 143, 'Completed', 'Closed', '13:15'),
('YZ7531', 'Takeoff/Landing', 'Arrived', 29, 'Completed', 'Closed', '14:00'),

-- CRUISE
('AA4826', 'Cruise', 'On Time', 118, 'Completed', 'Closed', '14:45'),
('BB9174', 'Cruise', 'Delayed', 164, 'Completed', 'Closed', '15:30'),
('CC6401', 'Cruise', 'On Time', 189, 'Completed', 'Closed', '16:15'),
('DD3589', 'Cruise', 'Delayed', 76, 'Completed', 'Closed', '17:00');


-- EVENTS TABLE

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    flight_number VARCHAR(20) UNIQUE NOT NULL,
    autopilot_status VARCHAR(20) NOT NULL,
    cabin_pressure DECIMAL(4,2) NOT NULL,
    wifi_usage INTEGER NOT NULL,
    FOREIGN KEY (flight_number) REFERENCES flights(flight_number)
);

INSERT INTO events (
    flight_number,
    autopilot_status,
    cabin_pressure,
    wifi_usage
)
VALUES

-- PARKED
('AB1234', 'OFF', 9.20, 15),
('CD5678', 'OFF', 9.10, 22),
('EF9012', 'OFF', 9.30, 18),
('GH3456', 'OFF', 9.00, 25),

-- TAXIING
('JK7890', 'OFF', 9.50, 35),
('LM1235', 'OFF', 9.60, 42),
('NP6789', 'OFF', 9.55, 38),
('QR2468', 'OFF', 9.65, 47),

-- TAKEOFF/LANDING
('ST1357', 'OFF', 10.10, 12),
('UV9753', 'OFF', 10.30, 8),
('WX8642', 'OFF', 10.20, 10),
('YZ7531', 'OFF', 9.90, 14),

-- CRUISE
('AA4826', 'ON', 10.60, 145),
('BB9174', 'ON', 10.55, 172),
('CC6401', 'ON', 10.50, 138),
('DD3589', 'ON', 10.65, 160);


-- JOIN QUERY

SELECT
    f.flight_number,
    f.simple_status,
    f.detailed_status,
    f.passenger_boarding_number,
    f.fueling,
    f.door_state,
    f.push_back_time,
    e.autopilot_status,
    e.cabin_pressure,
    e.wifi_usage
FROM flights f
INNER JOIN events e
ON f.flight_number = e.flight_number;