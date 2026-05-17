--- LÖVE callbacks — top-level assignment to the global ``love`` table.
--- Each callback is a public-API hook the engine invokes by name.

local player_x = 0
local player_speed = 200

function love.load()
    print("game starting")
end

function love.update(dt)
    player_x = player_x + player_speed * dt
end

function love.draw()
    love.graphics.print("x: " .. player_x, 10, 10)
end

function love.keypressed(key)
    if key == "escape" then
        love.event.quit()
    end
end
