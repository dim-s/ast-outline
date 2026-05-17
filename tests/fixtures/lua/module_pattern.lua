--- Greeter module — the canonical Lua module shape:
--- ``local M = {} ... return M``.
local M = {}

--- Greets a single name.
function M.greet(name)
    return "hello " .. name
end

-- A private helper, not exposed via ``return M``.
local function _normalize(name)
    return name:lower()
end

--- Greets several names in sequence.
function M.greet_all(names)
    local out = {}
    for i, n in ipairs(names) do
        out[i] = M.greet(_normalize(n))
    end
    return out
end

M.DEFAULT_GREETING = "hello"

return M
