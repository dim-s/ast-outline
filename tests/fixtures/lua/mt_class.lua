--- ``setmetatable``-based class — the second canonical Lua OOP pattern.
local Animal = {}
Animal.__index = Animal

--- Construct a new Animal.
function Animal.new(name, sound)
    local self = setmetatable({}, Animal)
    self.name = name
    self.sound = sound
    return self
end

--- Instance method: implicit ``self`` via the ``:`` operator.
function Animal:speak()
    return self.name .. " says " .. self.sound
end

function Animal:rename(new_name)
    self.name = new_name
end

-- Metamethods exercised as both method-style and assignment-style.
function Animal:__tostring()
    return "<Animal " .. self.name .. ">"
end

Animal.__eq = function(a, b)
    return a.name == b.name
end

return Animal
