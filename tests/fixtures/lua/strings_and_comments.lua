--- Long strings and block comments — for noise_regions coverage.

--[[
   This is a multi-line block comment.
   It mentions a function name like mentioned_in_comment so a
   grep for that name should report KIND_COMMENT, not KIND_REF.
]]

--[==[
   Level-2 long-bracket comment: the closer needs two equals signs
   to balance the opener. Also mentions shadow_function for grep.
]==]

local query = [[
SELECT *
FROM users
WHERE name = 'fake_function_call'
]]

local template = [==[
embedded text with ]] inside that does not close the level-2 form
mentions another_shadow_name
]==]

function public_fn()
    return query, template
end
