from re import match

import discord
import asyncio

class DropdownBar(discord.ui.View):
    def __init__(self, items, client, active_items, action_map, mode="default"):
        """
        :param items: The full list of objects to display in the dropdown
        :param data_client: The API/Client used to interact with the items (e.g., Docker client)
        :param active_items: A set/list of items currently marked as 'Active' or 'Monitored'
        :param toggle_callback: The function to execute when the toggle button is clicked
        """
        super().__init__(timeout=60.0)
        self.message = None
        self.items = items
        self.data_client = client
        self.active_items = active_items  if active_items is not None else set()
        self.selected_value = None
        self.action_map = action_map
        self.mode = mode
        
        # Add Exit button
        exit_btn = discord.ui.Button(label="Exit", style=discord.ButtonStyle.secondary, row=1)
        exit_btn.callback = self.exit_callback
        self.add_item(exit_btn)
        
        # Initialize specialized Select Menu
        self.add_item(GenericSelect(self.items, self.active_items, self.action_map, self.mode))
        
    def refresh_ui(self):
        """Update buttons and dropdown based on current state"""
        # Remove dynamic buttons
        for item in list(self.children):
            if isinstance(item, discord.ui.Button) and item.label != "Exit":
                self.remove_item(item)
                
        if self.selected_value:
            # Generate buttons based on action_map
            for label, (callback_func, style) in self.action_map.items():
                
                # Logic for toggle (enable/disable)
                actual_label = label
                actual_style = style
                if label == "Toggle":
                    is_active = self.selected_value in self.active_items
                    actual_label = "Disable" if is_active else "Enable"
                    actual_style = discord.ButtonStyle.danger if is_active else discord.ButtonStyle.success
                    
                btn = discord.ui.Button(label=actual_label, style=actual_style, row=1)
                btn.callback = self._make_callback(callback_func, actual_label)
                self.add_item(btn)

    def _make_callback(self, callback_func, label):
        async def internal_callback(interaction: discord.Interaction):
            # 1. Lock UI
            for item in self.children: 
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            # 2. Execute Logic
            # Note: callback_func in the Cog MUST accept (item_name, action_label)
            success, embed = await callback_func(self.selected_value, label)
            await asyncio.sleep(1)
            
            # 3. Unlock & Cleanup
            for item in list(self.children):
                if isinstance(item, discord.ui.Button) and item.label != "Exit":
                    self.remove_item(item)
                else:
                    item.disabled = False
            
            # 4. REFRESH DATA: Sync container statuses before updating Select Menu
            if hasattr(self.data_client, 'containers'):
                self.items = self.data_client.containers.list(all=True)

            for item in self.children:
                if isinstance(item, GenericSelect):
                    # Update items and emojis based on new status/active list
                    item.items = self.items 
                    item.update_options(self.active_items)

            await interaction.edit_original_response(embed=embed, view=self)
            self.selected_value = None

        return internal_callback
    
    async def on_timeout(self):
        await self.close_session_logic()
        
    async def exit_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="🔒 Session closed.", view=None)
        
    async def close_session_logic(self, interaction: discord.Interaction = None):
        self.stop()
        self.clear_items()
        
        content = "🔒 Session closed."
        
        try:
            if interaction:
                # Nếu thoát bằng nút bấm
                await interaction.response.edit_message(content=content, view=None, embed=None)
            elif self.message:
                # Nếu tự động đóng do timeout (dùng self.message đã lưu từ Cog)
                await self.message.edit(content=content, view=None, embed=None)
        except (discord.NotFound, discord.HTTPException):
            # Phòng trường hợp tin nhắn đã bị xóa trước đó
            pass

class GenericSelect(discord.ui.Select):
    def __init__(self, items, active_items, action_map, mode):
        self.items = items
        self.action_map = action_map
        self.mode = mode
        options = self._build_options(active_items, self.mode)
        super().__init__(
            placeholder="Select an item...", 
            options=options, 
            row=0
        )
    
    def _build_options(self, active_items, mode):
        """Builds list of SelectOptions. Customize 'label' and 'description' attributes here."""
        m_list = active_items if active_items is not None else []
        options = []
        
        for obj in self.items:
            name = getattr(obj, 'name', str(obj))
            status = getattr(obj, 'status', 'Unknown')
            
            if mode == "docker":
                emoji = "🐳" if status == "running" else "🔴"
                
            else:
                emoji = "🟢" if name in m_list else "🔴"
            
            options.append(discord.SelectOption(
                label=name,
                emoji=emoji,
                description=f"Status: {status}"
            ))
        
        return options
        
    def update_options(self, active_items):
        self.options = self._build_options(active_items, self.mode)
        
    async def callback(self, interaction: discord.Interaction):
        self.view.selected_value = self.values[0]
        for opt in self.options: 
            opt.default = (opt.label == self.values[0])
        self.view.refresh_ui()
        await interaction.response.edit_message(view=self.view)