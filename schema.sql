-- schema.sql content

CREATE TABLE Category (
  id INTEGER PRIMARY KEY,
  name TEXT,
  name_en TEXT,
  description TEXT,
  description_en TEXT
);

CREATE TABLE Item (
    -- *** IMPORTANT: Added PRIMARY KEY (id) for proper lookup ***
  id INTEGER PRIMARY KEY,
  name TEXT,
  name_en TEXT,
  description TEXT,
  description_en TEXT,
  status TEXT,
  restrictions TEXT,
  restrictions_en TEXT,
  category_id INTEGER,
  source TEXT,
  last_updated INTEGER
);
