-- change column type
ALTER TABLE ingredient 
    ALTER COLUMN name_kr TYPE varchar;
-- change column name
ALTER TABLE ingredient 
    RENAME COLUMN name_kr TO name_kr;
-- Change column comment
COMMENT ON COLUMN ingredient.name_kr IS 'comment';