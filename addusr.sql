CREATE USER 'gps'@'localhost' IDENTIFIED BY 'gpsTrackerP@ssW0rd!';
GRANT ALL PRIVILEGES ON gps.* TO 'gps'@'localhost';
FLUSH PRIVILEGES;