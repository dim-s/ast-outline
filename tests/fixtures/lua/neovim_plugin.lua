--- Neovim plugin module — the typical ``M.setup(opts)`` shape that
--- every plugin in the ecosystem follows.
local M = {}

M.config = {
    enabled = true,
    keymap = "<leader>x",
}

--- Apply user options to the plugin's config table.
function M.setup(opts)
    opts = opts or {}
    for k, v in pairs(opts) do
        M.config[k] = v
    end
    vim.keymap.set("n", M.config.keymap, M.run, { desc = "Run plugin" })
end

function M.run()
    if not M.config.enabled then return end
    print("plugin: running")
end

-- Internal helper, NOT exposed.
local function _validate(opts)
    return type(opts) == "table"
end

return M
