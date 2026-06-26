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
VALUES (
    'AB1234',
    'Ready for departure',
    128,
    'Completed',
    'Closed',
    '13:45'
)
ON CONFLICT (flight_number) DO NOTHING;
