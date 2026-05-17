--- Exercises every require shape + Lua 5.4 attribute markers.
require "socket"
require("socket.http")
local json = require("dkjson")
local ltn12 = require "ltn12"
local pkg = require("foo.bar.baz")

-- Lua 5.4 const / close attributes — should land in ``attrs``.
local PI <const> = 3.14159
local FILE <close> = io.open("/tmp/x", "w")

local M = {}

function M.fetch(url)
    -- Conditional require — inside a function body. Should NOT
    -- appear in the static imports list, only bump conditional_count.
    local body = require("socket.http").request(url)
    return json.decode(body)
end

return M
