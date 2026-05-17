-- Valid declaration before the break — adapter should surface it.
function ok_fn()
    return 1
end

-- Intentional syntax error: unclosed parameter list.
function broken_fn(
    -- never closes

-- A valid local after the break — adapter may or may not recover.
local AFTER = 42
