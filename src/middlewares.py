#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import List
from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware

admin_buttons = ['/log', '/statistics']
class AccessMiddleware(BaseMiddleware):
    def __init__(self, admins_ids: List[int]):
        self.admins_ids = admins_ids
        super().__init__()
    
    async def on_process_message(self, message: types.Message, _):
        if message.from_user.id not in self.admins_ids and message.get_command() in admin_buttons:
            raise CancelHandler()

