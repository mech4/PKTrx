import com.ihsan.foundation.pobjecthelper as phelper
import com.ihsan.labs.m_textreport as textreport

def PrintReport(helper, config, param):
  corporate = helper.CreateObject('Corporate')
  
  reportdef = config.HomeDir + 'reports/productdistribution.mtr'
  oReport = textreport.TextReport(reportdef)  
  
  # Set Title
  oReport.SetVars('BRANCH', param.BranchCode)
  if param.IsAllProduct == 'T':
    oReport.SetVars('ACCOUNT', 'SEMUA PRODUK')
    currencyCode = str(param.GetFieldByName('LProductAccount.CurrencyCode'))
    if currencyCode == None: currencyCode = '000'
    oReport.SetVars('CURRENCY', currencyCode)
  else:
    accountNo = param.GetFieldByName('LProductAccount.AccountNo')
    accountName = param.GetFieldByName('LProductAccount.AccountName')     
    oReport.SetVars('ACCOUNT', '%s-%s' % (accountNo, accountName))
    oReport.SetVars('CURRENCY', param.GetFieldByName('LProductAccount.CurrencyCode'))
  
  aBeginDate = param.BeginDate
  aEndDate = param.EndDate
  oReport.SetVars('BDATE', config.FormatDateTime('dd-mm-yyyy', aBeginDate))
  oReport.SetVars('EDATE', config.FormatDateTime('dd-mm-yyyy', aEndDate))
  
  # Set nama file output.txt
  reportFile = corporate.GetUserHomeDir() + '\\Rep_ProductDistribution.txt'
  oReport.OpenReport(reportFile)
  
  try:
    qParam = {}
    qParam['BDATE'] = config.FormatDateTime('yyyy-mm-dd', aBeginDate) 
    qParam['EDATE'] = config.FormatDateTime('yyyy-mm-dd', aEndDate) 
    
    if param.IsAllProduct == 'T':
      qParam['BRANCH'] = param.BranchCode
      qParam['CURRENCY'] = currencyCode
       
      sSQL = "\
        select t.TransactionDate, t.ReferenceNo, f.AccountName, \
          t.Description, i.Amount, t.Inputer, \
          t.AuthStatus, t.TransactionId \
        from accounttransactionitem a, transactionitem i, \
          transaction t, financialaccount f, productaccount p \
        where a.TransactionItemId = i.TransactionItemId \
          and i.TransactionId = t.TransactionId \
          and a.AccountNo = f.AccountNo \
          and f.AccountNo = p.AccountNo \
          and t.TransactionCode = 'DD001' \
          and t.TransactionDate >= '%(BDATE)s' \
          and t.TransactionDate <= '%(EDATE)s' \
          and i.BranchCode = '%(BRANCH)s' \
          and i.CurrencyCode = '%(CURRENCY)s' \
        order by t.TransactionDate, t.TransactionId \
      " % qParam
    else:
      qParam['ACCOUNT'] = accountNo
            
      sSQL = "\
        select t.TransactionDate, t.ReferenceNo, i.Description as AccountName, \
          t.Description, i.Amount, t.Inputer, \
          t.AuthStatus, t.TransactionId \
        from accounttransactionitem a, transactionitem i, \
          transaction t \
        where a.TransactionItemId = i.TransactionItemId \
          and a.AccountNo = '%(ACCOUNT)s' \
          and i.TransactionId = t.TransactionId \
          and t.TransactionCode = 'DD001' \
          and t.TransactionDate >= '%(BDATE)s' \
          and t.TransactionDate <= '%(EDATE)s' \
        order by t.TransactionDate, t.TransactionId \
      " % qParam
    
    res = config.CreateSQL(sSQL).rawresult
    while not res.Eof:
      aContent = {}
      aDate = res.TransactionDate
      aContent['DATE']        = '%2d-%2d-%4d' % (aDate[2], aDate[1], aDate[0])
      aContent['REFNO']       = res.ReferenceNo
      aContent['ACCOUNT']     = res.AccountName
      aContent['DESCRIPTION'] = res.Description
      aContent['AMOUNT']      = config.FormatFloat(',0.00', res.Amount)
      aContent['INPUTER']     = res.Inputer
      aContent['AUTHSTATUS']  = res.AuthStatus
      
      oReport.PrintRow('detail', aContent)
       
      res.Next()
    #-- while
    
  finally:
    oReport.Close()
  
  return reportFile
    
def DAFScriptMain(config, params, returns):
  # config: ISysConfig object
  # parameter: TPClassUIDataPacket
  # returnpacket: TPClassUIDataPacket (undefined structure)
  helper = phelper.PObjectHelper(config)    
  param = params.FirstRecord
  
  sw = returns.AddStreamWrapper()
  reportFile = PrintReport(helper, config, param)
  
  sw.LoadFromFile(reportFile)
  sw.MIMEType = config.AppObject.GetMIMETypeFromExtension(reportFile)

  return 1
