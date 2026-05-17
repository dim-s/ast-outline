--- Nested module / namespace pattern — multi-level dotted names
--- and method-style decls inside nested namespaces.
local ns = {}
ns.deep = {}
ns.deep.nested = {}

function ns.deep.nested.helper(x)
    return x * 2
end

function ns.deep:methodOnNested(y)
    return self.x + y
end

ns.deep.CONFIG = { mode = "fast" }

return ns
