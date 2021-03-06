import com.ihsan.foundation.pobjecthelper as phelper
import sys
import simplejson


def FormSetDataEx(uideflist, params) :
  config = uideflist.config
  helper = phelper.PObjectHelper(config)
  Now = int(config.Now())
  
  if params.GetDatasetByName('trparam') != None :
    oForm = helper.CreateObject('FormTransaksi')
    st = oForm.SetDataEx(uideflist,params)

    rec = uideflist.uipTransaction.Dataset.GetRecord(0)

    if rec.FundEntity in [None, '', 0] :
      rec.FundEntity = 2
      
    return st

  rec = uideflist.uipTransaction.Dataset.AddRecord()
  rec.Inputer = str(config.SecurityContext.UserId)
  rec.BranchCode = str(config.SecurityContext.GetUserInfo()[4])
  rec.BranchName = str(config.SecurityContext.GetUserInfo()[5])
  rec.TransactionDate = Now
  rec.ActualDate = Now
  rec.FloatTransactionDate = Now
  rec.Amount = 0.0
  
  # Set Transaction Number
  oService = helper.LoadScript('Transaction.TransactionHelper')
  rec.TransactionNo = '<AUTOGENERATED>' #oService.GetTransactionNumber(config,'CA')


def SimpanData(config, params, returns):
  IsErr = 0
  ErrMessage = ''
  TransactionNo = ''
  StreamName = ''
  
  helper = phelper.PObjectHelper(config)
  try :
    oTransaction = params.uipTransaction.GetRecord(0)

    request = {}
    #request['BatchId'] = oTransaction.GetFieldByName('LBatch.BatchId')
    request['ActualDate'] = oTransaction.ActualDate
    request['DestBranchCode'] = oTransaction.GetFieldByName('LBranchDestination.BranchCode')
    request['SourceAccountNo'] = oTransaction.GetFieldByName('LCashAccount.AccountNo')
    request['DestAccountNo'] = oTransaction.GetFieldByName('LCashAccountDestination.AccountNo')
    
    request['AccountNo'] = oTransaction.AccountNo
    request['Amount'] = oTransaction.Amount
    request['ReferenceNo'] = oTransaction.ReferenceNo
    request['Description'] = oTransaction.Description
    request['Rate'] = 1.0
    request['Inputer'] = config.SecurityContext.InitUser
    request['BranchCode'] = config.SecurityContext.GetUserInfo()[4]
    request['TransactionNo'] = oTransaction.TransactionNo
    request['PaidTo'] = oTransaction.PaidTo
    request['BudgetCode'] = oTransaction.BudgetCode or ''
    request['BudgetId'] = oTransaction.BudgetId or 0
    
    sRequest = simplejson.dumps(request)
    
    oService = helper.LoadScript('Transaction.GeneralTransaction')

    TransactionCode = 'DT'
    if oTransaction.ShowMode == 1:
      response = oService.CreateTransaction(TransactionCode, config, sRequest, params)
    else:
      response = oService.UpdateTransaction(TransactionCode, config, sRequest, params)
    # end if
    
    response = simplejson.loads(response)
    TransactionNo = response[u'TransactionNo']

    filename = response[u'FileKwitansi']

    sw = returns.AddStreamWrapper()
    sw.Name = 'Kwitansi'
    sw.LoadFromFile(filename)
    #sw.MIMEType = config.AppObject.GetMIMETypeFromExtension(filename)
    sw.MIMEType = 'application/msword'
    
    StreamName = sw.Name

    IsErr = response[u'Status']
    ErrMessage = response[u'ErrMessage']
    
  except :
    IsErr = 1
    ErrMessage = str(sys.exc_info()[1])

  returns.CreateValues(
     ['IsErr', IsErr],
     ['ErrMessage', ErrMessage],
     ['TransactionNo',TransactionNo],
     ['StreamName',StreamName],
     )

