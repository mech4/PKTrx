class fFixedAssetView:
  def __init__(self,formObj,parentObj):
    self.form = formObj
    self.app = formObj.ClientApplication
    self.FormView = None
    
  def Show(self,AccountNo):
    ph = self.app.CreateValues(['AccountNo',AccountNo])
    self.FormObject.SetDataWithParameters(ph)
    self.FormContainer.Show()

