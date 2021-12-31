from NTU.cool import Cool, Fool

c = Cool()
f = Fool(c)

c.update()

print('\n開始下載課程內容附件...')
print(*(c.courses[c.semester]), sep='\n')
search = input('請選擇課程: ')
c.download(search) # 先只下載一門課
f.build()