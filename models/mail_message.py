# from odoo import models, _, api, exceptions


# class MailMessage(models.Model):
#     _inherit = 'mail.message'


#     def unlink(self):
#         print("Delete the mail")
#         # if self.env.user.has_group('stock.group_stock_manager') == False:
#         raise exceptions.UserError(_("You cannot edit or delete messages in the stock movement!"))
#         # return super(MailMessage, self).unlink()

#     # @api.model
#     # def write(self, vals):
#     #     if self.env.user.has_group('stock.group_stock_manager') == False and self.model == "stock.picking":
#     #         raise exceptions.UserError(_("You cannot edit or delete messages in the stock movement!"))
#     #     return super(MailMessage, self).write(vals)
        
#     # @api.model
#     # def unlink(self):
#     #     if self.env.user.has_group('stock.group_stock_manager') == False:
#     #         raise exceptions.ValidationError(_("You cannot delete!"))
#     #     return super().unlink()



# from odoo import models, _, exceptions


# class MailMessage(models.Model):
#     _inherit = 'mail.message'

#     def unlink(self):
#         # أي محاولة حذف رسالة ستُمنع
#         raise exceptions.UserError(_("You cannot delete messages!"))


# class MailThread(models.AbstractModel):
#     _inherit = 'mail.thread'

#     def message_delete(self, message_ids=None):
#         raise exceptions.UserError(_("You cannot delete messages from chatter!"))
