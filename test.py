import datetime
import os
import sys
import csv
from time import sleep

count_of_tests = 1

target_branches = ["master"]
src_path = "/home/heroboec/tests/qemu/"
path_to_qemu = "/home/heroboec/tests/qemu/x86_64-softmmu/qemu-system-x86_64"
path_to_imgs = "/home/heroboec/benchmark/imgs/"
path_to_tests = "/home/heroboec/benchmark/tests/"

enable_replay_mode = 0
enable_kvm_mode = 1
enable_simple_mode = 0
MINIMAL_TEST_TIME = 5

mode = {'record':"record", 'replay':'replay', 'none': 'none', 'kvm': 'kvm'}



kvm_cmd = '''{} -drive file={},if=none,id=drv,snapshot -device ide-hd,drive=drv -drive file={},if=none,id=tst,snapshot -device ide-hd,drive=tst -net none -monitor stdio --enable-kvm -m 2G'''


cmd = '''{} -drive file={},if=none,id=drv,snapshot -device ide-hd,drive=drv -drive file={},if=none,id=tst,snapshot -device ide-hd,drive=tst -net none -monitor stdio -m 2G -icount auto'''


replay_cmd = '''{} -drive file={},if=none,id=drv,snapshot -drive driver=blkreplay,if=none,image=drv,id=drv_replay -device ide-hd,drive=drv_replay -drive file={},if=none,id=tst,snapshot -drive driver=blkreplay,if=none,image=tst,id=drv_tst_replay -device ide-hd,drive=drv_tst_replay -net none -icount shift=5,rr={},rrfile=record.bin -monitor stdio -m 2G'''


def getSeconds(t1, t2):
    result = t2-t1
    return result.seconds



def getTime(lst, index):
    if index > len(lst)-1:
        return 0
    else:
        return lst[index]['time']


def getReturnValue(lst, index):
    if index > len(lst)-1:
        return 0
    else:
        return lst[index]['retValue']


def switchBranchAndMake(src_path, br):
    os.system('''cd {};
                 git checkout {};
                 git pull;
                 make'''.format(src_path, br))



def saveReport(result, branch):
    print(result)
    with open(branch+'_report.csv', 'w') as csvfile:
        fieldnames = ['image-name', 'test-name', 'record',  'record retVal', 'record avg time', 'replay', 'replay retVal', 'replay avg time', 'kvm', 'kvm retVal', 'kvm avg time', 'none', 'none retVal', 'none avg time']
        print(fieldnames)

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()

        for image in result:
            row = {'image-name': image['image-name']}
            for test in image['tests']:
                row['test-name'] = test['test-name']
                sumForRecordMode = 0
                sumForReplayMode = 0
                sumForKvmMode = 0
                sumForNoneMode = 0
                for i in range(count_of_tests):
                    if i == 1:
                        row['image-name'] = ""
                        row['test-name'] = ""

                    row['record'] = getTime(test['record'], i)
                    row['replay'] = getTime(test['replay'], i)
                    row['none'] = getTime(test['none'], i)
                    row['kvm'] = getTime(test['kvm'], i)

                    row['record retVal'] = getReturnValue(test['record'], i)
                    row['replay retVal'] = getReturnValue(test['replay'], i)
                    row['none retVal'] = getReturnValue(test['none'], i)
                    row['kvm retVal'] = getReturnValue(test['kvm'], i)

                    sumForRecordMode += int(getTime(test['record'], i))
                    sumForReplayMode += int(getTime(test['replay'], i))
                    sumForKvmMode += int(getTime(test['kvm'], i))
                    sumForNoneMode += int(getTime(test['none'], i))

                    if i == count_of_tests - 1:
                        row['record avg time'] = sumForRecordMode/count_of_tests
                        row['replay avg time'] = sumForReplayMode/count_of_tests
                        row['kvm avg time'] = sumForKvmMode/count_of_tests
                        row['none avg time'] = sumForNoneMode/count_of_tests
                    writer.writerow(row)
                    row.clear()




def makeTests(branch):
    result = []
    global mode
    print(datetime.datetime.now())
    switchBranchAndMake(src_path, branch)

    for image in os.listdir(path_to_imgs):
        result.append({'image-name': image, 'tests': [] })
        for test in os.listdir(path_to_tests):
            result[-1]['tests'].append({'test-name': test, mode['record']: [], mode['replay']: [], mode['none']: [], mode['kvm']: []})
            for i in range(count_of_tests):
                if enable_replay_mode:

                    testStart = datetime.datetime.now()
                    print("command: ", replay_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test, mode['record']))
                    ret = os.system(replay_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test, mode['record']))
                    testStop = datetime.datetime.now()
                    result[-1]['tests'][-1]['record'].append({'time': getSeconds(testStart, testStop), 'retValue': ret})

                    testStart = datetime.datetime.now()
                    print("command: ", replay_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test, mode['replay']))
                    ret = os.system(replay_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test, mode['replay']))
                    testStop = datetime.datetime.now()
                    result[-1]['tests'][-1]['replay'].append({'time': getSeconds(testStart, testStop), 'retValue': ret})

                if enable_kvm_mode:

                    try_count = 3
                    while True:
                        testStart = datetime.datetime.now()
                        print("command: ", kvm_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test))
                        ret = os.system(kvm_cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test))
                        # print(ret)
                        testStop = datetime.datetime.now()
                        result[-1]['tests'][-1]['kvm'].append({'time': getSeconds(testStart, testStop), 'retValue': ret})
                        try_count -= 1
                        if getSeconds(testStart, testStop) > MINIMAL_TEST_TIME or try_count == 0:
                            sleep(10)
                            break



                if enable_simple_mode:
                    testStart = datetime.datetime.now()
                    print("command: ", cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test))
                    ret = os.system(cmd.format(path_to_qemu, path_to_imgs+image , path_to_tests+test))
                    testStop = datetime.datetime.now()
                    result[-1]['tests'][-1]['none'].append({'time': getSeconds(testStart, testStop), 'retValue': ret})
                print()
                sleep(10)

    saveReport(result, branch)

def main():
    for branch in target_branches:
        makeTests(branch)

if __name__ == "__main__":
    main()
