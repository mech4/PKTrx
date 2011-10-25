class fSelectProgram :
  def __init__(self, formObj, parentForm) :
    self.app = formObj.ClientApplication
    self.ProductId = None
    self.ProductName = None
    self.FundCategory = None
    self.PercentageOfAmilFunds = 0.0

  def OnDoubleClick(self,sender):
    self.FormObject.Close(1)
    
  def GetProduct(self, branchCode):
    self.qProduct.OQLText = "\
      select from VProduct \
        [status = 'A' and \
         BranchCode = :BranchCode and \
         ((currencycode ='000' and producttype = 'G') or (producttype='J')) ] \
      (ProductId, AccountName, ProductName, \
       FundCategory $ as FundType, \
       FundCategory, \
       PercentageOfAmilFunds, \
       ProductCode, \
       Idx,\
       AccountNo, self) \
      then order by ProductCode;"
    self.qProduct.SetParameter('BranchCode', branchCode)
    self.qProduct.DisplayData()
    
    st = self.FormContainer.Show()
    if st == 1:
      self.ProductId = self.qProduct.GetFieldValue('VProduct.ProductId')
      self.ProductName = self.qProduct.GetFieldValue('VProduct.AccountName')
      self.FundCategory = self.qProduct.GetFieldValue('VProduct.FundCategory')
      self.PercentageOfAmilFunds = self.qProduct.GetFieldValue('VProduct.PercentageOfAmilFunds')
      self.AccountNo = self.qProduct.GetFieldValue('VProduct.AccountNo')

    return st



